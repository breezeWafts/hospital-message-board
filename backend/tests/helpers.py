"""测试辅助函数。"""
import io


def login(client, username: str, password: str):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def auth_headers(client, username: str, password: str) -> dict:
    r = login(client, username, password)
    assert r.status_code == 200, f"登录失败: {r.text}"
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def submit_message(client, title="病房空调故障", content="夏天病房空调不制冷，请尽快处理",
                   files=None):
    """匿名提交留言。files: list[(filename, bytes)]。返回响应。"""
    payload = {}
    if files:
        payload = [
            ("attachments", (name, io.BytesIO(data), "application/octet-stream"))
            for name, data in files
        ]
    r = client.post(
        "/api/anonymous/messages",
        data={"title": title, "content": content},
        files=payload or None,
    )
    assert r.status_code == 200, f"提交失败: {r.text}"
    body = r.json()
    return body["id"], body["captcha"]


def run_full_pipeline(client, seeded, dept_keys=("OUTPATIENT", "LOGISTICS")):
    """完整流程：提交→秘书审核→院长批示→分派→各部门提交→秘书通过→院长确认。

    返回 (msg_id, captcha, task_ids)。
    """
    users = seeded["users"]
    depts = seeded["departments"]
    msg_id, captcha = submit_message(client)

    h_sec = auth_headers(client, *users["secretary"])
    r = client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "NEW"  # 秘书审核通过后仍为 NEW

    h_pri = auth_headers(client, *users["principal"])
    r = client.post(
        f"/api/principal/messages/{msg_id}/instruction",
        json={"instruction": "请门诊部与后勤保障部尽快处理并反馈"}, headers=h_pri,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING"

    r = client.post(
        f"/api/secretary/messages/{msg_id}/tasks/assign",
        json={"tasks": [
            {"department_id": depts[k], "title": f"{k}处理任务", "content": "请核实并处理"}
            for k in dept_keys
        ]},
        headers=h_sec,
    )
    assert r.status_code == 200, r.text
    task_ids = r.json()["task_ids"]

    dept_usernames = {
        "OUTPATIENT": "dept_user1",
        "LOGISTICS": "dept_user2",
    }
    for k, tid in zip(dept_keys, task_ids):
        dh = auth_headers(client, dept_usernames[k], "dept12345")
        r = client.post(
            f"/api/department/tasks/{tid}/submit",
            data={"content": f"{k}已处理完成"},
            headers=dh,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "REVIEWING"
        r = client.post(
            f"/api/secretary/tasks/{tid}/review", json={"result": "APPROVED"}, headers=h_sec
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "APPROVED"

    r = client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED"
    return msg_id, captcha, task_ids
