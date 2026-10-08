"""匿名功能测试：提交、查询可见性、验证码锁定与重置、附件类型拦截、评价。"""
import io

from helpers import auth_headers, run_full_pipeline, submit_message


def test_submit_returns_id_and_6_digit_captcha(client, seeded):
    msg_id, captcha = submit_message(client)
    assert isinstance(msg_id, int) and msg_id > 0
    assert len(captcha) == 6 and captcha.isdigit()
    from app.db import database as db

    row = db.one("SELECT status, submit_ip, submit_ua FROM messages WHERE id = %s", (msg_id,))
    assert row["status"] == "NEW"
    assert row["submit_ip"]  # 匿名留言额外记录提交 IP 与 UA


def test_query_before_completion_shows_minimal(client, seeded):
    msg_id, captcha = submit_message(client)
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "NEW"
    assert "tasks" not in body and "attachments" not in body  # 未通过不暴露附件与批注


def test_captcha_wrong_5_times_locks(client, seeded):
    msg_id, captcha = submit_message(client)
    for i in range(4):
        r = client.post("/api/anonymous/messages/query",
                        json={"id": msg_id, "captcha": "000000" if captcha != "000000" else "000001"})
        assert r.status_code == 400
        assert r.json()["detail"]["attempts_left"] == 4 - i
    r = client.post("/api/anonymous/messages/query",
                    json={"id": msg_id, "captcha": "000000" if captcha != "000000" else "000001"})
    assert r.status_code == 400
    assert r.json()["detail"]["attempts_left"] == 0
    # 正确验证码也被锁定
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 423
    assert "locked_until" in r.json()["detail"]


def test_admin_reset_captcha_unlock_only(client, seeded):
    msg_id, captcha = submit_message(client)
    wrong = "000000" if captcha != "000000" else "000001"
    for _ in range(5):
        client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": wrong})
    h = auth_headers(client, "admin", "admin123")
    r = client.post("/api/admin/messages/reset-captcha", json={"message_id": msg_id}, headers=h)
    assert r.status_code == 200
    from app.db import database as db

    row = db.one("SELECT captcha_attempts, captcha_locked_until, captcha_hash FROM messages WHERE id = %s",
                 (msg_id,))
    assert row["captcha_attempts"] == 0
    assert row["captcha_locked_until"] is None
    # 验证码未变：原验证码仍可查询
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 200


def test_captcha_expired(client, seeded):
    msg_id, captcha = submit_message(client)
    from app.db import database as db

    db.execute("UPDATE messages SET captcha_expires_at = now() - interval '1 day' WHERE id = %s", (msg_id,))
    r = client.post("/api/anonymous/messages/query", json={"id": msg_id, "captcha": captcha})
    assert r.status_code == 400
    assert "过期" in r.json()["detail"]


def test_executable_and_disallowed_upload_blocked(client, seeded):
    r = client.post(
        "/api/anonymous/messages",
        data={"title": "t", "content": "c"},
        files=[("attachments", ("virus.exe", io.BytesIO(b"MZ..."), "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "禁止" in r.json()["detail"]
    r = client.post(
        "/api/anonymous/messages",
        data={"title": "t", "content": "c"},
        files=[("attachments", ("note.txt", io.BytesIO(b"hello"), "text/plain"))],
    )
    assert r.status_code == 400


def test_oversize_upload_blocked(client, seeded, monkeypatch):
    from app.services import config_service

    monkeypatch.setattr(config_service, "get_int", lambda k, d: 1 if k == "max_file_size_mb" else d)
    r = client.post(
        "/api/anonymous/messages",
        data={"title": "t", "content": "c"},
        files=[("attachments", ("big.png", io.BytesIO(b"0" * (1024 * 1024 + 1)), "image/png"))],
    )
    assert r.status_code == 400
    assert "MB" in r.json()["detail"]


def test_evaluate_satisfied_archives_and_dissatisfied_keeps_completed(client, seeded):
    msg1, cap1, _ = run_full_pipeline(client, seeded)
    r = client.post(f"/api/anonymous/messages/{msg1}/evaluate",
                    json={"captcha": cap1, "satisfied": True, "content": "处理得很好"})
    assert r.status_code == 200
    assert r.json()["status"] == "ARCHIVED"
    assert r.json()["evaluation_satisfied"] is True
    # 已评价不可重复评价
    r = client.post(f"/api/anonymous/messages/{msg1}/evaluate",
                    json={"captcha": cap1, "satisfied": True})
    assert r.status_code == 400

    msg2, cap2, _ = run_full_pipeline(client, seeded)
    r = client.post(f"/api/anonymous/messages/{msg2}/evaluate",
                    json={"captcha": cap2, "satisfied": False, "content": "处理不及时"})
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"
    assert r.json()["evaluation_satisfied"] is False


def test_evaluate_requires_completed(client, seeded):
    msg_id, captcha = submit_message(client)
    r = client.post(f"/api/anonymous/messages/{msg_id}/evaluate",
                    json={"captcha": captcha, "satisfied": True})
    assert r.status_code == 400


def test_evaluate_wrong_captcha_rejected(client, seeded):
    msg_id, captcha, _ = run_full_pipeline(client, seeded)
    r = client.post(f"/api/anonymous/messages/{msg_id}/evaluate",
                    json={"captcha": "000000" if captcha != "000000" else "000001", "satisfied": True})
    assert r.status_code == 400
