# 医院匿名留言板系统

匿名提交、秘书审核、院长批示、部门处理、匿名查询评价的全流程留言板。前后端分离，医疗系统配色，响应式适配 PC / 手机 / 平板。

- **后端**：Python + FastAPI + psycopg2（无 ORM、纯 SQL）+ 自研连接池 + 自研迁移器 + JWT + bcrypt + PostgreSQL 18
- **前端**：Vue 3 + TypeScript + Vite + Pinia + Vue Router + axios + Vue Flow（工作流图）
- **部署**：Docker Compose（PostgreSQL / 后端 / 前端 / Nginx），Nginx 负责静态资源、反向代理、附件受控转发

## 目录结构

```
hospital-message-board/
├── backend/
│   ├── app/
│   │   ├── main.py                # 应用入口：CORS、防刷中间件、健康检查
│   │   ├── constants.py           # 枚举与审计动作常量
│   │   ├── schemas.py             # Pydantic 模型
│   │   ├── core/
│   │   │   ├── config.py          # .env 配置（system_configs 的兜底）
│   │   │   ├── security.py        # bcrypt / JWT / 验证码哈希 / OAuth state / 匿名下载令牌
│   │   │   ├── deps.py            # 当前用户、角色鉴权、IP/UA
│   │   │   └── ratelimit.py       # IP 限流 + 自动黑名单 + 匿名提交冷却
│   │   ├── db/
│   │   │   └── database.py        # 自研连接池（LifoQueue）+ 执行封装 + SQL 安全工具（单文件）
│   │   ├── services/              # config / audit / notification / attachment / user /
│   │   │                          # department / message / task 服务（SQL 常量集中在模块顶部）
│   │   └── api/                   # auth / anonymous / principal / secretary / department /
│   │                              # admin / attachment 路由
│   ├── migrations/V001__init_schema.sql
│   ├── scripts/                   # migrate.py（自研迁移器）/ seed.py / entrypoint.py
│   ├── tests/                     # pytest 测试集（conftest + helpers + 4 个测试文件）
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                      # Vue 3 应用（含 Dockerfile 与 nginx.conf）
├── nginx/nginx.conf               # 入口反向代理
├── docker-compose.yml
├── .env.example
└── README.md
```

## 一、快速开始（Docker Compose 一键启动）

```bash
cp .env.example .env          # 按需修改（尤其 JWT_SECRET / CAPTCHA_SECRET）
docker compose up -d --build
```

启动后访问 `http://localhost:8080`（端口由 `.env` 的 `WEB_PORT` 控制）。

后端容器启动时自动：等待数据库 → 执行迁移 → 写入种子数据 → 启动 uvicorn。

### 默认账号（首次登录后必须修改密码）

| 角色 | 账号 | 初始密码 |
|---|---|---|
| 系统管理员 | admin | admin123 |
| 院长 | principal | principal123 |
| 秘书 | secretary | secretary123 |
| 部门负责人（门诊部） | department | department123 |

密码策略：至少 8 位，必须同时包含字母和数字。

## 二、本地开发

### 后端

```bash
# 1. 准备 PostgreSQL 18（UTF8），创建数据库：
#    createdb -E UTF8 hospital_board

# 2. 虚拟环境 + 依赖
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows；Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置
copy .env.example .env            # 修改 DATABASE_URL 等

# 4. 迁移 + 种子数据
python -m scripts.migrate
python -m scripts.seed

# 4.1（可选）模块导入冒烟检查
python -m scripts.check

# 5. 启动
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev                       # 开发服务器（已配置 /api 代理到 http://localhost:8000）
```

### 运行测试

```bash
cd backend
# 需要本机可连接 PostgreSQL（测试库默认 postgresql://postgres:postgres@127.0.0.1:5432/hmb_test，
# 可用 TEST_DATABASE_URL 覆盖；测试库不存在时会自动创建）
python -m pytest tests -v
```

测试覆盖：登录成功/失败/锁定、统一认证首次登录自动创建待授权用户、授权后可登录且不重复创建、
OAuth2 state 防重放、角色越权、匿名提交与查询、验证码错误 5 次锁定、管理员重置仅解锁不改验证码、
多部门完整流程、驳回流程、院长确认不通过→重新处理、附件可见性时点、可执行文件拦截、
SQL 注入防护（LIKE/排序/LIMIT）、日志完整性、通知 mock、匿名用户不接收通知、IP 黑名单。

## 三、业务流程与状态机

### 留言状态

```
NEW ──秘书审核通过──> NEW（待院长批示）──院长批示──> PENDING
 │
 └──秘书驳回/拒绝──> REJECTED ──归档──> ARCHIVED

PENDING ──部门提交──> REVIEWING
REVIEWING ──全部任务通过且院长确认──> COMPLETED
REVIEWING ──院长/秘书驳回──> PENDING
COMPLETED ──匿名评价满意 / 秘书归档──> ARCHIVED
COMPLETED ──匿名评价不满意──> COMPLETED（evaluation_satisfied = false）
```

- 秘书审核通过后留言**仍为 NEW**，通过 `secretary_review_result = APPROVED` 区分"待院长批示"；
  院长批示视图只查询 `status = NEW AND secretary_review_result = APPROVED`。
- 留言状态由任务状态聚合计算（任一任务 PENDING→PENDING；任一 REVIEWING→REVIEWING；
  全部 APPROVED 且院长未确认→保持 REVIEWING）；**ARCHIVED 与秘书驳回后的 REJECTED 不再被聚合重算覆盖**。
- 院长不直接分派部门：院长批示后，由**秘书**将留言分解为一个或多个部门任务并分派；
  每条留言可对应多个部门任务，每部门一条独立任务。
- 院长最终确认不通过 → 相关任务回到 PENDING、留言回到 PENDING，驳回到秘书重新处理。

### 任务状态

```
PENDING → REVIEWING → APPROVED（终态）
              ↓
           REJECTED → 回到 PENDING（保留 last_review_result / last_review_comment 与历史记录）
```

秘书可将驳回任务二次分派（再次调用分派接口，向原部门或新部门创建新任务），驳回历史全部保留。

### 匿名查询与评价

- 留言编号 = `messages.id`；查询验证码 = 6 位随机数字，有效期 30 天，只存哈希（sha256 + secret）。
- 错误 5 次锁定 30 天；管理员重置仅执行 `captcha_attempts = 0、captcha_locked_until = NULL`，
  **不重新生成验证码、不修改哈希**。
- 仅 `COMPLETED / ARCHIVED` 可查看完整处理历史（含驳回批注、部门处理内容、院长审核意见、已通过任务的附件）；
  未通过时不可见部门附件与驳回批注。
- 评价满意 → 自动归档；不满意 → 保持 COMPLETED 并标记不满意，通知秘书（秘书再通知院长，当前 mock）。
- 匿名用户不接收任何通知，自行凭编号与验证码查询。

## 四、角色与权限

| 角色 | 代码 | 权限 |
|---|---|---|
| 系统管理员 | admin | 维护部门、创建账号、修改系统配置、查看日志、重置验证码锁定、统一认证用户授权；不参与留言审核/分派/处理/评价 |
| 院长 | principal | 查看秘书审核通过的留言、批示、最终确认/驳回 |
| 秘书 | secretary | 查看全部留言、审核、分派任务、逐任务审核、归档 |
| 部门负责人 | department | 仅本部门任务：查看、上传附件、填写处理内容、提交 |
| 匿名用户 | 无账号 | 提交留言、凭编号+验证码查询、评价 |

## 五、登录与统一认证

- **本地账号**：管理员后台创建；失败 5 次锁定 15 分钟；用户可自行修改密码。
- **统一认证（自定义 OAuth2 授权码模式）**：登录页选择"统一认证"跳转认证中心，返回字段
  `userId / name / phone / email`。后端完成 code 换 token 与 userinfo 获取：
  - 首次登录按 `userId` 自动创建本地用户（`auth_source=oauth2`、`username=userId`（冲突追加后缀）、
    `role` 为空、`is_active=false`），**等待管理员分配角色、部门并启用**后才可以进入业务；
  - 已绑定用户再次登录更新 name/phone/email，并校验本地 `is_active` 与 `role`；
  - 登录成功后由**本系统签发本地 JWT**，不直接使用统一认证 token 访问业务接口；
  - 回调必须校验 `state`（存 `oauth_states` 表：state、redirect_uri、created_at、expires_at、used），防 CSRF；
  - 本地权限独立授权，不信任统一认证中心角色。
- OAuth2 配置：`OAUTH2_*` 环境变量（.env 兜底），也可写入 `system_configs` 表后台修改。

## 六、附件规则

- 允许：`jpg/jpeg/png/gif/bmp/webp`、`pdf`、`doc/docx`、`xls/xlsx`、`ppt/pptx`；
  禁止可执行文件（exe/bat/cmd/sh/com/scr/msi/jar/vbs/js/ps1/dll/so/app/dmg/php/jsp/asp 等），
  白名单 + 黑名单**双保险**拦截。
- 单文件 ≤ 20 MB，单次 ≤ 10 个（均可在后台 `system_configs` 修改，settings/.env 兜底）。
- 存储：服务器本地目录，按 `YYYY/MM/DD/uuid.ext` 分目录；原始文件名仅存库展示，不用于路径拼接。
- **附件下载必须经过后端鉴权**（`/api/attachments/*`），Nginx 不直接暴露附件存储目录。可见性：

| 角色 | 可见附件 |
|---|---|
| 院长 | 秘书审核通过的匿名留言附件；任务附件仅在该任务被秘书审核通过后可见；最终确认前可查看所有已通过任务的处理内容与附件 |
| 秘书/管理员 | 全部 |
| 部门 | 仅本部门任务相关附件 |
| 匿名用户 | 仅自身留言相关且任务已通过的附件（凭查询接口返回的短时效签名下载令牌） |

## 七、日志与通知

- 全流程日志写入 `audit_logs`，字段固定：操作人、角色、IP、UA、时间、动作、前状态、后状态、留言 ID、任务 ID。
  **只追加不修改、永久保留**；匿名留言额外记录提交时的 IP 与 User-Agent。
- 通知当前为 **mock**：所有触发点写入 `notifications` 表（`status = MOCKED`），抽象为
  `notification_service`，后续可无侵入替换为短信/邮件。
  触发点：匿名提交→秘书；秘书审核通过→院长；院长批示→秘书；分派→部门；部门提交→秘书；
  全部任务通过→院长最终确认；匿名评价→秘书（不满意时秘书再通知院长）。
  秘书驳回/拒绝、院长确认完成**不通知匿名用户**。

## 八、安全

- 前后端防抖：前端所有提交按钮 loading 防重复点击；后端 IP 限流（滑动窗口）+ 匿名提交冷却 +
  超阈值自动加入 `ip_blacklist`（管理员可查看/解除：`GET/DELETE /api/admin/blacklist`）。
- SQL 注入防护：全部值 `%s` 参数化；表名/列名/排序方向白名单；动态 IN 按参数个数生成占位符；
  LIKE 转义 `\ % _` 配合 `ESCAPE`；LIMIT/OFFSET 强制 int 并限制上限；每次 execute 仅一条 SQL。
- 登录失败锁定、验证码锁定、JWT、bcrypt、OAuth2 state 校验、统一认证用户默认未授权，按技术约束执行。

## 九、API 一览

| 分组 | 方法与路径 | 说明 |
|---|---|---|
| 认证 | POST /api/auth/login | 本地账号登录 |
| | POST /api/auth/change-password | 修改密码 |
| | GET /api/auth/me | 当前用户 |
| | GET /api/auth/oauth2/login | 跳转统一认证授权页 |
| | GET /api/auth/oauth2/callback | 授权回调（校验 state） |
| 匿名 | POST /api/anonymous/messages | 提交留言（multipart） |
| | POST /api/anonymous/messages/query | 查询（id + captcha） |
| | POST /api/anonymous/messages/{id}/evaluate | 评价 |
| 院长 | GET /api/principal/messages?view=instruction\|confirm\|all | 留言列表（默认待批示） |
| | GET /api/principal/messages/{id} | 留言详情 |
| | POST /api/principal/messages/{id}/instruction | 批示并通知秘书分解任务 |
| | POST /api/principal/messages/{id}/confirm | 最终确认完成 |
| | POST /api/principal/messages/{id}/reject | 确认不通过，驳回到秘书 |
| | GET /api/principal/tasks/{task_id} | 任务详情 |
| 秘书 | GET /api/secretary/messages | 全部留言（筛选/搜索/分页） |
| | GET /api/secretary/messages/{id} | 留言详情 |
| | POST /api/secretary/messages/{id}/review | 审核：通过/驳回/拒绝 |
| | POST /api/secretary/messages/{id}/tasks/assign | 分解并分派部门任务（含二次分派） |
| | GET /api/secretary/departments | 启用中的部门列表（分派下拉，实现补充） |
| | GET /api/secretary/tasks | 任务列表 |
| | GET /api/secretary/tasks/{task_id} | 任务详情 |
| | POST /api/secretary/tasks/{task_id}/review | 审核任务：通过/驳回 |
| | POST /api/secretary/messages/{id}/archive | 归档 |
| 部门 | GET /api/department/tasks | 本部门任务 |
| | GET /api/department/tasks/{id} | 任务详情 |
| | POST /api/department/tasks/{id}/submit | 上传附件、填写处理内容、提交 |
| 管理员 | GET/POST /api/admin/users、PATCH /api/admin/users/{id} | 用户管理（含统一认证用户授权） |
| | GET/POST /api/admin/departments、PATCH /api/admin/departments/{id} | 部门管理 |
| | GET/PUT /api/admin/configs | 系统配置 |
| | POST /api/admin/messages/reset-captcha | 仅解除验证码锁定 |
| | GET /api/admin/logs | 日志查询 |
| | GET /api/admin/blacklist、DELETE /api/admin/blacklist/{ip} | IP 黑名单（扩展） |
| 附件 | GET /api/attachments/message/{att_id} | 留言附件（后端鉴权） |
| | GET /api/attachments/task/{att_id} | 任务附件（后端鉴权） |
| 健康 | GET /api/health | 健康检查 |

## 十、系统配置项（后台可改，settings/.env 兜底）

| config_key | 默认值 | 说明 |
|---|---|---|
| max_file_size_mb | 20 | 单文件大小上限（MB） |
| max_files_per_submit | 10 | 单次上传数量上限 |
| captcha_ttl_days | 30 | 查询验证码有效期（天） |
| captcha_max_attempts | 5 | 验证码最大错误次数 |
| captcha_lock_days | 30 | 验证码锁定时长（天） |
| login_max_attempts | 5 | 登录失败锁定阈值 |
| login_lock_minutes | 15 | 登录锁定时长（分钟） |
| rate_limit_max_requests | 120 | IP 限流阈值（次/窗口） |
| rate_limit_window_seconds | 60 | 限流窗口（秒） |
| blacklist_ban_seconds | 86400 | 自动拉黑时长（秒） |
| anon_submit_cooldown_seconds | 10 | 匿名提交冷却（秒） |

## 十一、部署说明（Debian + Nginx）

1. 服务器安装 Docker 与 Docker Compose 插件。
2. 上传项目目录，`cp .env.example .env` 并修改密钥与统一认证配置。
3. `docker compose up -d --build`，Nginx 监听 `WEB_PORT`（默认 8080）。
4. 生产建议：`WEB_PORT=80`，前端域名写入 `FRONTEND_BASE_URL` 与 `CORS_ORIGINS`，
   统一认证回调地址 `OAUTH2_REDIRECT_URI=https://域名/api/auth/oauth2/callback`，
   数据库数据卷（pgdata）与附件卷（uploads）定期备份；附件存储目录仅后端容器挂载，Nginx 不暴露。

## 十二、实现口径备忘（v2.2）

- 匿名用户无账号；留言编号即 `messages.id`；验证码 6 位随机数字、只存哈希。
- 留言状态由任务状态聚合，但 ARCHIVED 与秘书驳回后的 REJECTED 不再被聚合重算覆盖。
- 秘书审核通过后仍为 NEW，院长视图只查询 `status = NEW AND secretary_review_result = APPROVED`。
- 通知当前 mock，只写 notifications 表；匿名用户不接收通知，自行查询。
- 管理员重置验证码仅解除锁定（attempts=0、locked_until=NULL），不重新生成、不改哈希。
- 日志只追加不修改、永久保留；统一认证本地权限独立授权；回调校验 state 防 CSRF。
