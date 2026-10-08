"""认证测试：登录成功/失败/锁定、改密策略、角色越权、统一认证、管理员用户维护。"""
import pytest

from helpers import auth_headers, login


def test_login_success_and_me(client, seeded):
    r = login(client, "secretary", "secretary123")
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["role"] == "secretary"
    r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert r2.status_code == 200
    assert r2.json()["username"] == "secretary"


def test_login_wrong_password(client, seeded):
    r = login(client, "secretary", "wrong-pass-123")
    assert r.status_code == 401


def test_login_lock_after_5_failures(client, seeded):
    for _ in range(4):
        assert login(client, "secretary", "wrong-pass-123").status_code == 401
    r = login(client, "secretary", "wrong-pass-123")
    assert r.status_code == 401
    # 第 5 次失败后锁定：即使密码正确也拒绝
    r = login(client, "secretary", "secretary123")
    assert r.status_code == 423
    assert "locked_until" in r.json()["detail"]


def test_change_password_policy(client, seeded):
    h = auth_headers(client, "secretary", "secretary123")
    # 太短
    assert client.post("/api/auth/change-password",
                       json={"old_password": "secretary123", "new_password": "abc1"},
                       headers=h).status_code == 400
    # 无字母
    assert client.post("/api/auth/change-password",
                       json={"old_password": "secretary123", "new_password": "12345678"},
                       headers=h).status_code == 400
    # 无数字
    assert client.post("/api/auth/change-password",
                       json={"old_password": "secretary123", "new_password": "abcdefgh"},
                       headers=h).status_code == 400
    # 原密码错误
    assert client.post("/api/auth/change-password",
                       json={"old_password": "wrong-old-1", "new_password": "newpass123"},
                       headers=h).status_code == 400
    # 正常修改
    r = client.post("/api/auth/change-password",
                    json={"old_password": "secretary123", "new_password": "newpass123"},
                    headers=h)
    assert r.status_code == 200
    assert login(client, "secretary", "newpass123").status_code == 200
    assert login(client, "secretary", "secretary123").status_code == 401


def test_role_forbidden(client, seeded):
    # 院长调秘书接口
    h_pri = auth_headers(client, "principal", "principal123")
    assert client.get("/api/secretary/messages", headers=h_pri).status_code == 403
    # 部门调管理员接口
    h_dept = auth_headers(client, "dept_user1", "dept12345")
    assert client.get("/api/admin/users", headers=h_dept).status_code == 403
    # 无 token
    assert client.get("/api/secretary/messages").status_code == 401
    # 秘书调管理员接口
    h_sec = auth_headers(client, "secretary", "secretary123")
    assert client.get("/api/admin/logs", headers=h_sec).status_code == 403


def test_admin_user_crud(client, seeded):
    h = auth_headers(client, "admin", "admin123")
    r = client.post("/api/admin/users", json={
        "username": "doctor_zhang", "password": "zhang1234", "display_name": "张医生",
        "role": "department", "department_id": seeded["departments"]["OUTPATIENT"],
    }, headers=h)
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    assert r.json()["must_change_password"] is True
    # 列表
    r = client.get("/api/admin/users?search=doctor", headers=h)
    assert r.json()["total"] == 1
    # 修改（授权统一认证用户同样走此接口）
    r = client.patch(f"/api/admin/users/{uid}", json={"is_active": False}, headers=h)
    assert r.json()["is_active"] is False
    # 密码策略校验
    r = client.post("/api/admin/users", json={
        "username": "bad_pw_user", "password": "short", "role": "secretary",
    }, headers=h)
    assert r.status_code == 400
    # 部门负责人必须指定部门
    r = client.post("/api/admin/users", json={
        "username": "no_dept_user", "password": "valid1234", "role": "department",
    }, headers=h)
    assert r.status_code == 400


def test_admin_reset_password_and_login(client, seeded):
    """管理员重置用户密码（参数顺序回归：update_user 带密码更新）。"""
    h = auth_headers(client, "admin", "admin123")
    r = client.get("/api/admin/users", params={"search": "secretary"}, headers=h)
    uid = r.json()["items"][0]["id"]
    r = client.patch(f"/api/admin/users/{uid}", json={"password": "reset1234"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is True
    # 新密码可登录，旧密码失效
    assert login(client, "secretary", "reset1234").status_code == 200
    assert login(client, "secretary", "secretary123").status_code == 401


def test_admin_configs_update_returns_new_values(client, seeded):
    """PUT /api/admin/configs 返回值必须包含本次更新（事务内同一连接读取回归）。"""
    h = auth_headers(client, "admin", "admin123")
    r = client.put("/api/admin/configs", json={"configs": {"max_file_size_mb": "5"}}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["configs"]["max_file_size_mb"] == "5"
    r = client.get("/api/admin/configs", headers=h)
    assert r.json()["configs"]["max_file_size_mb"] == "5"


# ---------------- 统一认证（OAuth2）----------------

def _oauth_state(client):
    r = client.get("/api/auth/oauth2/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(r.headers["location"]).query)
    return qs["state"][0]


def _mock_oauth(monkeypatch, userinfo):
    import httpx

    class FakeTokenResp:
        status_code = 200

        def json(self):
            return {"access_token": "fake-access-token"}

    class FakeInfoResp:
        status_code = 200

        def json(self):
            return userinfo

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeTokenResp())
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeInfoResp())


def test_oauth_first_login_creates_pending_user(client, seeded, monkeypatch):
    _mock_oauth(monkeypatch, {"userId": "u10086", "name": "李医生", "phone": "13800000000",
                              "email": "li@example.com"})
    state = _oauth_state(client)
    r = client.get(f"/api/auth/oauth2/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code in (302, 307)
    location = r.headers["location"]
    assert "pending=1" in location
    assert "token=" not in location
    from app.db import database as db

    user = db.one("SELECT * FROM users WHERE external_user_id = %s", ("u10086",))
    assert user is not None
    assert user["auth_source"] == "oauth2"
    assert user["role"] is None
    assert user["is_active"] is False
    assert user["username"] == "u10086"
    assert user["display_name"] == "李医生"


def test_oauth_authorized_user_can_login_without_duplicate(client, seeded, monkeypatch):
    _mock_oauth(monkeypatch, {"userId": "u20001", "name": "王主任", "phone": "13900000000",
                              "email": "wang@example.com"})
    # 首次登录：待授权
    state = _oauth_state(client)
    r = client.get(f"/api/auth/oauth2/callback?code=a&state={state}", follow_redirects=False)
    assert "pending=1" in r.headers["location"]
    # 管理员授权：分配角色、部门并启用
    h = auth_headers(client, "admin", "admin123")
    from app.db import database as db

    uid = db.scalar("SELECT id FROM users WHERE external_user_id = %s", ("u20001",))
    r = client.patch(
        f"/api/admin/users/{uid}",
        json={"role": "secretary", "is_active": True}, headers=h,
    )
    assert r.status_code == 200
    # 再次登录：签发本地 JWT，且不重复创建用户
    state = _oauth_state(client)
    r = client.get(f"/api/auth/oauth2/callback?code=b&state={state}", follow_redirects=False)
    location = r.headers["location"]
    assert "pending=0" in location
    assert "token=" in location
    count = db.scalar("SELECT count(*) AS c FROM users WHERE external_user_id = %s", ("u20001",))
    assert int(count) == 1


def test_oauth_state_replay_and_invalid_rejected(client, seeded, monkeypatch):
    _mock_oauth(monkeypatch, {"userId": "u30001", "name": "赵医生"})
    state = _oauth_state(client)
    r1 = client.get(f"/api/auth/oauth2/callback?code=x&state={state}", follow_redirects=False)
    assert r1.status_code in (302, 307)
    # 重放同一 state → 拒绝
    r2 = client.get(f"/api/auth/oauth2/callback?code=y&state={state}", follow_redirects=False)
    assert "error=" in r2.headers["location"]
    # 无效 state → 拒绝
    r3 = client.get("/api/auth/oauth2/callback?code=z&state=not-exist", follow_redirects=False)
    assert "error=" in r3.headers["location"]
