"""全流程与驳回流程测试：多部门完整流程、任务驳回、院长驳回、归档、附件可见性时点。"""
import io

from helpers import auth_headers, login, run_full_pipeline, submit_message


def test_full_flow_multi_department(client, seeded):
    """提交→秘书审核→院长批示→分派两部门→部门处理→秘书通过→院长确认→匿名查询→评价归档。"""
    msg_id, captcha, task_ids = run_full_pipeline(client, seeded)
    assert len(task_ids) == 2
    # 匿名查询：完整处理历史
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["can_evaluate"] is True
    assert len(body["tasks"]) == 2
    assert all(t["status"] == "APPROVED" for t in body["tasks"])
    assert body["principal_instruction"]
    wf = body["workflow"]
    assert wf["current"] == "COMPLETED"
    assert all(s["reached"] for s in wf["stages"] if s["key"] in
               ("SUBMITTED", "SECRETARY_REVIEW", "PRINCIPAL_INSTRUCTION",
                "DEPARTMENT_PROCESSING", "SECRETARY_TASK_REVIEW", "PRINCIPAL_CONFIRM"))
    # 评价满意自动归档
    r = client.post(f"/api/anonymous/messages/{msg_id}/evaluate",
                    json={"captcha": captcha, "satisfied": True})
    assert r.json()["status"] == "ARCHIVED"
    # 归档后仍可查询
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 200
    assert r.json()["status"] == "ARCHIVED"


def test_secretary_reject_flow(client, seeded):
    msg_id, captcha = submit_message(client)
    h_sec = auth_headers(client, "secretary", "secretary123")
    # 驳回必须填写原因
    r = client.post(f"/api/secretary/messages/{msg_id}/review",
                    json={"result": "REJECTED"}, headers=h_sec)
    assert r.status_code == 400
    r = client.post(f"/api/secretary/messages/{msg_id}/review",
                    json={"result": "REJECTED", "comment": "内容描述不清"}, headers=h_sec)
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"
    # 匿名用户可查询到驳回状态（不显示驳回原因细节，仅状态）
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.json()["status"] == "REJECTED"
    # 秘书归档驳回留言
    r = client.post(f"/api/secretary/messages/{msg_id}/archive", headers=h_sec)
    assert r.status_code == 200
    assert r.json()["status"] == "ARCHIVED"


def test_principal_instruction_requires_approved(client, seeded):
    msg_id, _ = submit_message(client)
    h_pri = auth_headers(client, "principal", "principal123")
    # 秘书未审核前院长不能批示
    r = client.post(f"/api/principal/messages/{msg_id}/instruction",
                    json={"instruction": "请处理"}, headers=h_pri)
    assert r.status_code == 400
    # 批示视图不包含未审核留言
    r = client.get("/api/principal/messages?view=instruction", headers=h_pri)
    assert r.json()["total"] == 0


def test_task_reject_then_resubmit(client, seeded):
    """驳回流程：驳回后回到 PENDING，保留批注；部门重新提交后可通过。"""
    users = seeded["users"]
    depts = seeded["departments"]
    msg_id, captcha = submit_message(client)
    h_sec = auth_headers(client, *users["secretary"])
    h_pri = auth_headers(client, *users["principal"])
    client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    client.post(f"/api/principal/messages/{msg_id}/instruction",
                json={"instruction": "请处理"}, headers=h_pri)
    r = client.post(f"/api/secretary/messages/{msg_id}/tasks/assign",
                    json={"tasks": [{"department_id": depts["OUTPATIENT"], "title": "门诊处理"}]},
                    headers=h_sec)
    task_id = r.json()["task_ids"][0]

    h_dept = auth_headers(client, "dept_user1", "dept12345")
    client.post(f"/api/department/tasks/{task_id}/submit",
                data={"content": "第一次处理"}, headers=h_dept)
    # 驳回必须填写批注
    r = client.post(f"/api/secretary/tasks/{task_id}/review",
                    json={"result": "REJECTED"}, headers=h_sec)
    assert r.status_code == 400
    r = client.post(f"/api/secretary/tasks/{task_id}/review",
                    json={"result": "REJECTED", "comment": "缺少处理照片"}, headers=h_sec)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["last_review_result"] == "REJECTED"
    assert body["last_review_comment"] == "缺少处理照片"
    assert len(body["reviews"]) == 1  # 驳回历史保留
    # 留言回到 PENDING
    r = client.get(f"/api/secretary/messages/{msg_id}", headers=h_sec)
    assert r.json()["status"] == "PENDING"
    # 部门重新提交并通过
    client.post(f"/api/department/tasks/{task_id}/submit",
                data={"content": "补充材料后再次提交"}, headers=h_dept)
    r = client.post(f"/api/secretary/tasks/{task_id}/review",
                    json={"result": "APPROVED"}, headers=h_sec)
    assert r.json()["status"] == "APPROVED"
    r = client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri)
    assert r.json()["status"] == "COMPLETED"
    # 匿名可查看完整历史（含驳回批注）
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert any(rv["result"] == "REJECTED" for rv in body["tasks"][0]["reviews"])
    assert any(loop["task_id"] == task_id for loop in body["workflow"]["loops"])


def test_principal_reject_then_confirm(client, seeded):
    """院长确认不通过→任务回到 PENDING→部门重新提交→确认完成。"""
    users = seeded["users"]
    depts = seeded["departments"]
    msg_id, captcha = submit_message(client)
    h_sec = auth_headers(client, *users["secretary"])
    h_pri = auth_headers(client, *users["principal"])
    client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    client.post(f"/api/principal/messages/{msg_id}/instruction",
                json={"instruction": "请处理"}, headers=h_pri)
    r = client.post(f"/api/secretary/messages/{msg_id}/tasks/assign",
                    json={"tasks": [{"department_id": depts["OUTPATIENT"], "title": "门诊处理"}]},
                    headers=h_sec)
    task_id = r.json()["task_ids"][0]
    h_dept = auth_headers(client, "dept_user1", "dept12345")
    client.post(f"/api/department/tasks/{task_id}/submit",
                data={"content": "已处理"}, headers=h_dept)
    client.post(f"/api/secretary/tasks/{task_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    # 院长确认不通过
    r = client.post(f"/api/principal/messages/{msg_id}/reject",
                    json={"comment": "处理不到位，重新处理"}, headers=h_pri)
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"
    # 任务回到 PENDING 且保留驳回记录
    r = client.get(f"/api/secretary/tasks/{task_id}", headers=h_sec)
    assert r.json()["status"] == "PENDING"
    assert r.json()["last_review_result"] == "REJECTED"
    # 部门重新处理 → 秘书通过 → 院长确认完成
    client.post(f"/api/department/tasks/{task_id}/submit",
                data={"content": "重新处理完毕"}, headers=h_dept)
    client.post(f"/api/secretary/tasks/{task_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    r = client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri)
    assert r.json()["status"] == "COMPLETED"


def test_principal_confirm_requires_all_tasks_approved(client, seeded):
    users = seeded["users"]
    depts = seeded["departments"]
    msg_id, _ = submit_message(client)
    h_sec = auth_headers(client, *users["secretary"])
    h_pri = auth_headers(client, *users["principal"])
    client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    client.post(f"/api/principal/messages/{msg_id}/instruction",
                json={"instruction": "请处理"}, headers=h_pri)
    r = client.post(f"/api/secretary/messages/{msg_id}/tasks/assign",
                    json={"tasks": [{"department_id": depts["OUTPATIENT"], "title": "门诊处理"}]},
                    headers=h_sec)
    task_id = r.json()["task_ids"][0]
    # 任务未提交/未通过时不能确认
    assert client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri).status_code == 400
    h_dept = auth_headers(client, "dept_user1", "dept12345")
    client.post(f"/api/department/tasks/{task_id}/submit", data={"content": "已处理"}, headers=h_dept)
    # 待秘书审核时院长也不能确认
    assert client.post(f"/api/principal/messages/{msg_id}/confirm", headers=h_pri).status_code == 400


def test_department_only_sees_own_tasks(client, seeded):
    users = seeded["users"]
    depts = seeded["departments"]
    msg_id, _ = submit_message(client)
    h_sec = auth_headers(client, *users["secretary"])
    h_pri = auth_headers(client, *users["principal"])
    client.post(f"/api/secretary/messages/{msg_id}/review", json={"result": "APPROVED"}, headers=h_sec)
    client.post(f"/api/principal/messages/{msg_id}/instruction",
                json={"instruction": "请处理"}, headers=h_pri)
    client.post(f"/api/secretary/messages/{msg_id}/tasks/assign",
                json={"tasks": [{"department_id": depts["OUTPATIENT"], "title": "门诊处理"}]},
                headers=h_sec)
    # 后勤部用户看不到门诊部任务
    h_dept2 = auth_headers(client, "dept_user2", "dept12345")
    r = client.get("/api/department/tasks", headers=h_dept2)
    assert r.json()["total"] == 0
    # 后勤部不能提交门诊部任务
    h_dept1 = auth_headers(client, "dept_user1", "dept12345")
    tid = client.get("/api/department/tasks", headers=h_dept1).json()["items"][0]["id"]
    r = client.post(f"/api/department/tasks/{tid}/submit",
                    data={"content": "越权提交"}, headers=h_dept2)
    assert r.status_code == 403
