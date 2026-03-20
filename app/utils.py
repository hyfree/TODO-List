"""纯工具函数（无副作用，无 IO）"""
import json
import re
import logging
from datetime import datetime, timezone, date

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fmt_date(d):
    if d is None:
        return None
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


def fmt_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(ts)


def row_to_task(row) -> dict | None:
    if row is None:
        return None
    t = dict(row)
    t["dueDate"] = fmt_date(t.pop("due_date", None))
    t["startDate"] = fmt_date(t.pop("start_date", None))
    t["createdAt"] = fmt_ts(t.pop("created_at", None))
    t["updatedAt"] = fmt_ts(t.pop("updated_at", None))
    t["completedAt"] = fmt_ts(t.pop("completed_at", None))
    for field in ("tags", "metadata", "notes"):
        val = t.get(field)
        default: list | dict = [] if field != "metadata" else {}
        if isinstance(val, str):
            try:
                t[field] = json.loads(val)
            except Exception:
                t[field] = default
        elif val is None:
            t[field] = default
    for k in ["dueDate", "startDate", "completedAt", "summary", "description", "detail"]:
        if t.get(k) is None:
            t.pop(k, None)
    return t


def new_id() -> str:
    """生成当天唯一任务 ID，格式：task-YYYYMMDD-NNN"""
    from .database import get_conn, put_conn

    date_str = datetime.now().strftime("%Y%m%d")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM todo_tasks WHERE id LIKE %s ORDER BY id DESC LIMIT 1",
                (f"task-{date_str}-%",),
            )
            row = cur.fetchone()
            seq = 1
            if row:
                m = re.search(r"-(\d+)$", row[0])
                seq = int(m.group(1)) + 1 if m else 1
        return f"task-{date_str}-{seq:03d}"
    finally:
        put_conn(conn)
