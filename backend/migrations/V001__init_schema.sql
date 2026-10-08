-- =============================================================
-- V001: 医院匿名留言板系统初始结构
-- 数据库：PostgreSQL 18，字符集 UTF8，时间 TIMESTAMPTZ
-- 说明：字段按需求 v2.2 保留，可按实现补充（tasks.processing_content、
--       users.must_change_password、ip_blacklist 等）。
-- 注意：schema_migrations 表由自研迁移器创建并维护。
-- =============================================================

CREATE TABLE departments (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,                                   -- 统一认证用户可为空
    display_name TEXT,
    phone TEXT,
    email TEXT,
    auth_source TEXT NOT NULL DEFAULT 'local' CHECK (auth_source IN ('local', 'oauth2')),
    external_user_id TEXT UNIQUE,                         -- 统一认证返回的 userId
    role TEXT CHECK (role IN ('admin', 'principal', 'secretary', 'department')),  -- 统一认证首次创建可为空
    department_id BIGINT REFERENCES departments(id),      -- 部门负责人必填
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN NOT NULL DEFAULT FALSE,  -- 补充：默认账号首次登录后强制改密
    failed_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,                             -- 留言编号即 messages.id
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('NEW', 'PENDING', 'REVIEWING', 'COMPLETED', 'REJECTED', 'ARCHIVED')),
    captcha_hash TEXT NOT NULL,                           -- sha256 + secret，不存明文
    captcha_attempts INT NOT NULL DEFAULT 0,
    captcha_locked_until TIMESTAMPTZ,
    captcha_expires_at TIMESTAMPTZ NOT NULL,
    submit_ip TEXT,
    submit_ua TEXT,
    evaluation_satisfied BOOLEAN,
    principal_instruction TEXT,
    secretary_review_result TEXT CHECK (secretary_review_result IN ('APPROVED', 'REJECTED', 'REFUSED')),
    secretary_reviewer_id BIGINT REFERENCES users(id),
    secretary_reviewed_at TIMESTAMPTZ,
    secretary_review_comment TEXT,
    completed_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE message_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,                          -- 原始文件名仅存库展示，不参与路径拼接
    stored_path TEXT NOT NULL,                            -- YYYY/MM/DD/uuid.ext（相对 upload_dir）
    mime_type TEXT,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    department_id BIGINT NOT NULL REFERENCES departments(id),
    assigner_id BIGINT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT,                                         -- 任务内容（秘书分派时填写）
    processing_content TEXT,                              -- 补充：部门处理内容
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'REVIEWING', 'APPROVED')),
    last_review_result TEXT CHECK (last_review_result IN ('APPROVED', 'REJECTED')),
    last_review_comment TEXT,
    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE task_attachments (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    task_id BIGINT REFERENCES tasks(id) ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES users(id),
    result TEXT NOT NULL,                                 -- APPROVED / REJECTED / REFUSED 等
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evaluations (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    satisfied BOOLEAN NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    channel TEXT NOT NULL,                                -- 当前 mock
    recipient TEXT,                                       -- 收件人（用户名/角色标识）
    subject TEXT,
    content TEXT,
    status TEXT NOT NULL DEFAULT 'MOCKED',
    related_type TEXT,                                    -- message / task
    related_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    operator_id BIGINT,
    operator_name TEXT,
    role TEXT,
    ip TEXT,
    ua TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,
    before_status TEXT,
    after_status TEXT,
    message_id BIGINT,
    task_id BIGINT
);

CREATE TABLE system_configs (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_by BIGINT REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE oauth_states (
    state TEXT PRIMARY KEY,
    redirect_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE ip_blacklist (
    id BIGSERIAL PRIMARY KEY,
    ip TEXT UNIQUE NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

-- 索引
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_secretary ON messages(status, secretary_review_result);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_message_attachments_message ON message_attachments(message_id);
CREATE INDEX idx_tasks_message ON tasks(message_id);
CREATE INDEX idx_tasks_dept_status ON tasks(department_id, status);
CREATE INDEX idx_task_attachments_task ON task_attachments(task_id);
CREATE INDEX idx_reviews_message ON reviews(message_id);
CREATE INDEX idx_reviews_task ON reviews(task_id);
CREATE INDEX idx_audit_message ON audit_logs(message_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_operator ON audit_logs(operator_id);
CREATE INDEX idx_notifications_created ON notifications(created_at);
CREATE INDEX idx_oauth_states_expires ON oauth_states(expires_at);
CREATE INDEX idx_ip_blacklist_expires ON ip_blacklist(expires_at);
