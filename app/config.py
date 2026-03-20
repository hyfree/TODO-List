"""全局配置"""
import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = "/home/hyfree/logs/todo-server.log"
HTML_FILE = "/home/hyfree/todo/todo-pro-kanban-v3.3.html"

PRIORITY_MAP = {"high": "P0", "medium": "P1", "low": "P2"}

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5433")),
    dbname=os.environ.get("DB_NAME", "narrative_db"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "postgres_password_change_me"),
)
