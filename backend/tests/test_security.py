"""安全测试：SQL 注入防护、附件可见性/鉴权下载、审计日志、通知 mock、黑名单。"""
import io

from helpers import auth_headers, run_full_pipeline, submit_message


def test_sql_injection_in_search_and_sort(client, seeded):
    for title in ("正常留言甲", "正常留言乙"):
        submit_message(client, title=title)
    h = auth_headers(client, "secretary", "secretary123")
    # LIKE 通配符按字面处理：搜索 "%" 不应命中任何记录
    r = client.get("/api/secretary/messages", params={"search": "%"}, headers=h)
    assert r.json()["total"] == 0
    # 注入语句按字面处理
    r = client.get("/api/secretary/messages",
                   params={"search": "' OR 1=1 --"}, headers=h)
    assert r.json()["total"] == 0
    # 非法排序参数回退默认（不报错、不注入）
    r = client.get("/api/secretary/messages",
                   params={"sort": "created_at DESC; DROP TABLE messages; --"}, headers=h)
    assert r.status_code == 200
    # 超大分页被限制上限
    r = client.get("/api/secretary/messages", params={"page_size": 999999}, headers=h)
    assert r.status_code == 200
    assert r.json()["page_size"] <= 100
    # 正常搜索命中
    r = client.get("/api/secretary/messages", params={"search": "正常留言甲"}, headers=h)
    assert r.json()["total"] == 1


def test_attachment_visibility_and_authorized_download(client, seeded):
    users = seeded["users"]
    depts = seeded["departments"]
    h_sec = auth_headers(client, *users["secretary"])
    h_pri = auth_headers(client, *users["principal"])
    msg_id, captcha = submit_message(
        client, files=[("报告.pdf", b"%PDF-1.4 fake content")]
    )
    att_id = _message_att_id(msg_id)
    # 秘书审核前：院长不可下载匿名留言附件
    assert client.get(f"/api/attachments/message/{att_id}", headers=h_pri).status_code == 403
    # 秘书可下载
    assert client.get(f"/api/attachments/message/{att_id}", headers=h_sec).status_code == 200
    # 匿名无令牌不可下载
    assert client.get(f"/api/attachments/message/{att_id}").status_code == 403

    client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    # 秘书审核通过后：院长可见匿名留言附件
    assert client.get(f"/api/attachments/message/{att_id}", headers=h_pri).status_code == 200

    client.post(f"/api/principal/messages/{msg_id}/instruction",
                json={"instruction": "请处理"}, headers=h_pri)
    r = client.post(f"/api/secretary/messages/{msg_id}/tasks/assign",
                    json={"tasks": [{"department_id": depts["OUTPATIENT"], "title": "门诊处理"}]},
                    headers=h_sec)
    task_id = r.json()["task_ids"][0]
    h_dept1 = auth_headers(client, "dept_user1", "dept12345")
    h_dept2 = auth_headers(client, "dept_user2", "dept12345")
    r = client.post(f"/api/department/tasks/{task_id}/submit",
                    data={"content": "已处理"},
                    files=[("attachments", ("证明.docx", io.BytesIO(b"PK fake docx"), "application/octet-stream"))],
                    headers=h_dept1)
    assert r.status_code == 200
    task_att_id = r.json()["attachments"][0]["id"]
    # 部门附件：审核通过前院长不可见
    assert client.get(f"/api/attachments/task/{task_att_id}", headers=h_pri).status_code == 403
    # 其他部门不可见
    assert client.get(f"/api/attachments/task/{task_att_id}", headers=h_dept2).status_code == 403
    # 本部门可见
    assert client.get(f"/api/attachments/task/{task_att_id}", headers=h_dept1).status_code == 200
    # 审核通过
    client.post(f"/api/secretary/tasks/{task_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    # 通过后院长可见
    assert client.get(f"/api/attachments/task/{task_att_id}", headers=h_pri).status_code == 200
    client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri)
    # 匿名：完成后凭令牌可下载（留言附件与已通过任务附件），无令牌 403
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    body = r.json()
    anon_url = body["attachments"][0]["download_url"]
    assert "anon_token=" in anon_url
    assert client.get(anon_url).status_code == 200
    task_url = body["tasks"][0]["attachments"][0]["download_url"]
    assert client.get(task_url).status_code == 200
    assert client.get(f"/api/attachments/message/{att_id}").status_code == 403


def _message_att_id(msg_id: int) -> int:
    from app.db import database as db

    return db.scalar("SELECT id FROM message_attachments WHERE message_id = %s", (msg_id,))


def test_audit_logs_append_only_and_complete(client, seeded):
    msg_id, _ = submit_message(client)
    h = auth_headers(client, "admin", "admin123")
    r = client.get("/api/admin/logs", params={"message_id": msg_id}, headers=h)
    assert r.status_code == 200
    actions = [item["action"] for item in r.json()["items"]]
    assert "ANON_SUBMIT" in actions
    # 匿名日志记录了 IP 与 UA
    item = next(i for i in r.json()["items"] if i["action"] == "ANON_SUBMIT")
    assert item["ip"] == "testclient"
    assert item["role"] == "anonymous"

    # 秘书审核 → 状态前后记录完整
    h_sec = auth_headers(client, "secretary", "secretary123")
    client.post(f"/api/secretary/messages/{msg_id}/review",
                json={"result": "REJECTED", "comment": "信息不全"}, headers=h_sec)
    r = client.get("/api/admin/logs", params={"message_id": msg_id, "action": "SECRETARY_REVIEW"}, headers=h)
    item = r.json()["items"][0]
    assert item["before_status"] == "NEW"
    assert item["after_status"] == "REJECTED"
    assert item["operator_name"] == "院长秘书"


def test_notifications_mock_written(client, seeded):
    from app.db import database as db

    msg_id, _ = submit_message(client)
    rows = db.all("SELECT * FROM notifications WHERE related_type = 'message' AND related_id = %s", (msg_id,))
    assert rows
    assert all(r["status"] == "MOCKED" for r in rows)
    assert all(r["channel"] == "mock" for r in rows)
    # 匿名提交 → 通知秘书；匿名用户不接收通知
    assert rows[0]["recipient"] == "secretary"
    # 所有通知收件人均为系统用户，无匿名收件人
    recipients = db.all("SELECT DISTINCT recipient FROM notifications")
    assert all(r["recipient"] in ("secretary", "principal", "dept_user1", "dept_user2", "admin")
               for r in recipients)

    # 秘书驳回 → 不通知匿名用户，通知表不新增匿名收件人
    h = auth_headers(client, "secretary", "secretary123")
    client.post(f"/api/secretary/messages/{msg_id}/review",
                json={"result": "REJECTED", "comment": "信息不全"}, headers=h)
    total = db.scalar("SELECT count(*) AS c FROM notifications WHERE related_id = %s", (msg_id,))
    # 秘书驳回仅记录审计日志，不写通知
    assert int(total) == 1

    # 评价触发通知秘书
    msg2, cap2, _ = run_full_pipeline(client, seeded)
    client.post(f"/api/anonymous/messages/{msg2}/evaluate",
                json={"captcha": cap2, "satisfied": True})
    rows = db.all("SELECT recipient FROM notifications WHERE related_id = %s", (msg2,))
    assert any(r["recipient"] == "secretary" for r in rows)


def test_ip_blacklist_blocks_requests(client, seeded):
    from app.core import ratelimit
    from app.db import database as db

    with db.tx() as conn:
        db.execute(
            "INSERT INTO ip_blacklist(ip, reason, expires_at) VALUES (%s, %s, now() + interval '1 hour')",
            ("testclient", "测试拉黑"), conn,
        )
    ratelimit._blacklist_cache["ts"] = 0  # 强制刷新黑名单缓存
    r = client.get("/api/health")
    assert r.status_code == 403
    # 解除后恢复
    db.execute("DELETE FROM ip_blacklist WHERE ip = %s", ("testclient",))
    ratelimit._blacklist_cache["ts"] = 0
    assert client.get("/api/health").status_code == 200
