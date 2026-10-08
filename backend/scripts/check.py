"""模块导入冒烟检查：验证全部后端模块可被导入（不依赖数据库连接）。

用法：
    python -m scripts.check

用途：部署前快速自检（编译/导入错误会在启动前暴露）。数据库相关检查
（迁移、种子、pytest）见 README。
"""
import importlib
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

MODULES = [
    "app.constants",
    "app.schemas",
    "app.core.config",
    "app.core.security",
    "app.core.deps",
    "app.core.ratelimit",
    "app.db.database",
    "app.services.config_service",
    "app.services.audit_service",
    "app.services.notification_service",
    "app.services.attachment_service",
    "app.services.user_service",
    "app.services.department_service",
    "app.services.message_service",
    "app.services.task_service",
    "app.api.router",
    "app.api.auth",
    "app.api.anonymous",
    "app.api.principal",
    "app.api.secretary",
    "app.api.department",
    "app.api.admin",
    "app.api.attachment",
    "app.main",
    "scripts.migrate",
    "scripts.seed",
]


def main() -> int:
    failed = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"  [OK]   {name}")
        except Exception as e:  # noqa: BLE001
            failed.append(name)
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
    if failed:
        print(f"\n检查失败：{len(failed)} 个模块导入异常")
        return 1
    print(f"\n全部 {len(MODULES)} 个模块导入正常。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
