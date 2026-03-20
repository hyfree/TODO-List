#!/usr/bin/env python3
"""
Todo List Server v6.0 - FastAPI
架构：FastAPI + Uvicorn → app 模块 → PostgreSQL

入口文件仅负责：日志配置 + 启动 uvicorn
业务逻辑见 app/ 各子模块。
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# ── 日志配置（必须在 app 导入前完成）─────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = "/home/hyfree/logs/todo-server.log"


def _setup_logging():
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    try:
        fh = RotatingFileHandler(
            LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except (OSError, PermissionError):
        pass  # 开发环境日志目录不存在时跳过文件日志


_setup_logging()

from app.main import app  # noqa: E402  # pylint: disable=wrong-import-position
from app.config import DB_CONFIG  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    print("Todo List Server v6.0 (FastAPI/Modular) starting...")
    print(f"   DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print("   API: http://0.0.0.0:5003/api/tasks")
    uvicorn.run(app, host="0.0.0.0", port=5003, log_level="info")