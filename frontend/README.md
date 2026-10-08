# 医院匿名留言板系统 —— 前端（Vue 3 + TypeScript + Vite）

技术栈：Vue 3 + TypeScript + Vite · Pinia · Vue Router · axios · Element Plus（全中文界面）· @vue-flow/core 工作流图。

## 开发

```bash
npm install
npm run dev        # http://localhost:5173，/api 代理到 http://localhost:8000
```

后端需在 `http://localhost:8000` 运行（见 `../backend`）。

## 构建

```bash
npm run build      # vue-tsc 类型检查 + vite 构建，产物在 dist/
npm run preview
```

## Docker

```bash
docker build -t hmb-frontend .
docker run -p 8080:80 hmb-frontend   # 需与后端容器同网络（/api 反代到 http://backend:8000）
```

## 页面一览

- 匿名端：`/`（提交留言）、`/submit/success`、`/query`（进度查询，含 Vue Flow 工作流与评价）、`/evaluate/:id`、`/oauth2/result`
- 登录：`/login`（本地账号 / 统一认证）、`/change-password`
- 院长：`/principal`（待批示/待最终确认/全部）、留言详情、任务详情
- 秘书：`/secretary`（留言列表/详情/分派/归档）、`/secretary/tasks`（任务列表/详情/审核）
- 部门：`/department`（本部门任务列表/详情/提交处理）
- 管理员：`/admin/users`、`/admin/departments`、`/admin/configs`、`/admin/logs`、`/admin/captcha-reset`、`/admin/blacklist`
