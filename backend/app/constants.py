"""全局常量：角色、状态机、审核结果、审计动作、附件限制默认值。"""


class Role:
    ADMIN = "admin"
    PRINCIPAL = "principal"
    SECRETARY = "secretary"
    DEPARTMENT = "department"
    ANONYMOUS = "anonymous"  # 匿名用户无账号
    SYSTEM = "system"        # 系统动作（如自动拉黑 IP）
    ALL_STAFF = (ADMIN, PRINCIPAL, SECRETARY, DEPARTMENT)


class MessageStatus:
    NEW = "NEW"
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    ALL = (NEW, PENDING, REVIEWING, COMPLETED, REJECTED, ARCHIVED)
    # 匿名用户可查看完整处理历史的终态集合
    ANON_VIEWABLE = (COMPLETED, ARCHIVED)


class TaskStatus:
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    ALL = (PENDING, REVIEWING, APPROVED)


class SecretaryReview:
    """秘书审核匿名留言的结果（秘书审核通过后留言仍为 NEW）。"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUSED = "REFUSED"
    ALL = (APPROVED, REJECTED, REFUSED)


class TaskReview:
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditAction:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    OAUTH_LOGIN = "OAUTH_LOGIN"
    ANON_SUBMIT = "ANON_SUBMIT"
    ANON_QUERY = "ANON_QUERY"
    ANON_QUERY_FAILED = "ANON_QUERY_FAILED"
    ANON_EVALUATE = "ANON_EVALUATE"
    SECRETARY_REVIEW = "SECRETARY_REVIEW"
    PRINCIPAL_INSTRUCTION = "PRINCIPAL_INSTRUCTION"
    TASKS_ASSIGNED = "TASKS_ASSIGNED"
    TASK_SUBMIT = "TASK_SUBMIT"
    TASK_REVIEW = "TASK_REVIEW"
    PRINCIPAL_CONFIRM = "PRINCIPAL_CONFIRM"
    PRINCIPAL_REJECT = "PRINCIPAL_REJECT"
    ARCHIVE = "ARCHIVE"
    CAPTCHA_RESET = "CAPTCHA_RESET"
    IP_BLACKLISTED = "IP_BLACKLISTED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    DEPARTMENT_CREATED = "DEPARTMENT_CREATED"
    DEPARTMENT_UPDATED = "DEPARTMENT_UPDATED"
    CONFIG_UPDATED = "CONFIG_UPDATED"


# ---- 附件限制默认值（可被 system_configs 覆盖，settings/.env 兜底）----
DEFAULT_MAX_FILE_SIZE_MB = 20
DEFAULT_MAX_FILES_PER_SUBMIT = 10

ALLOWED_EXTENSIONS = {
    # 图片
    "jpg", "jpeg", "png", "gif", "bmp", "webp",
    # PDF
    "pdf",
    # Office
    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
}

# 禁止类型（双保险：即使白名单被误改也拦截）
BLOCKED_EXTENSIONS = {
    "exe", "bat", "cmd", "sh", "com", "scr", "msi", "jar", "vbs", "js",
    "ps1", "dll", "so", "app", "dmg", "php", "jsp", "asp", "aspx", "cgi",
    "py", "pyc", "rb", "pl", "bin", "reg", "lnk", "wsf", "hta", "apk",
}

# 验证码 / 锁定默认值
DEFAULT_CAPTCHA_TTL_DAYS = 30
DEFAULT_CAPTCHA_MAX_ATTEMPTS = 5
DEFAULT_CAPTCHA_LOCK_DAYS = 30

# 登录锁定默认值
DEFAULT_LOGIN_MAX_ATTEMPTS = 5
DEFAULT_LOGIN_LOCK_MINUTES = 15

# 防刷默认值
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 120
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_BLACKLIST_BAN_SECONDS = 86400
DEFAULT_ANON_SUBMIT_COOLDOWN_SECONDS = 10

ROLE_LABELS = {
    Role.ADMIN: "系统管理员",
    Role.PRINCIPAL: "院长",
    Role.SECRETARY: "秘书",
    Role.DEPARTMENT: "部门负责人",
}

STATUS_LABELS = {
    MessageStatus.NEW: "待秘书审核",
    MessageStatus.PENDING: "部门处理中",
    MessageStatus.REVIEWING: "待复核/待院长确认",
    MessageStatus.COMPLETED: "已完成",
    MessageStatus.REJECTED: "已驳回",
    MessageStatus.ARCHIVED: "已归档",
}

TASK_STATUS_LABELS = {
    TaskStatus.PENDING: "待处理",
    TaskStatus.REVIEWING: "待秘书审核",
    TaskStatus.APPROVED: "已通过",
}
