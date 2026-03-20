"""统计分析查询"""
import logging
from psycopg2.extras import RealDictCursor
from ..database import get_conn, put_conn

logger = logging.getLogger(__name__)


def overview() -> dict:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='completed') AS completed,
                    COUNT(*) FILTER (WHERE status='pending') AS pending,
                    COUNT(*) FILTER (WHERE status='progress') AS progress,
                    COUNT(*) FILTER (WHERE status='cancelled') AS cancelled
                FROM todo_tasks
                """
            )
            counts = dict(cur.fetchone())

            cur.execute(
                "SELECT priority, COUNT(*) AS cnt FROM todo_tasks GROUP BY priority ORDER BY priority"
            )
            priority_dist = {r["priority"]: r["cnt"] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT tag, COUNT(*) AS cnt FROM (
                    SELECT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                    UNION ALL
                    SELECT jsonb_array_elements_text(tags)
                    FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ) t GROUP BY tag ORDER BY cnt DESC LIMIT 20
                """
            )
            tag_dist = {r["tag"]: r["cnt"] for r in cur.fetchall()}

        return {**counts, "priority_dist": priority_dist, "tag_dist": tag_dist}
    finally:
        put_conn(conn)


def trend() -> dict:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DATE(completed_at AT TIME ZONE 'Asia/Shanghai') AS day, COUNT(*) AS cnt
                FROM todo_tasks
                WHERE completed_at IS NOT NULL
                  AND completed_at >= NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
                """
            )
            completed_by_day = {str(r["day"]): r["cnt"] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT DATE(created_at AT TIME ZONE 'Asia/Shanghai') AS day, COUNT(*) AS cnt
                FROM todo_tasks
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
                """
            )
            created_by_day = {str(r["day"]): r["cnt"] for r in cur.fetchall()}

        return {"completed_by_day": completed_by_day, "created_by_day": created_by_day}
    finally:
        put_conn(conn)


def priority() -> list:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT priority, COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status='completed') AS completed
                FROM todo_tasks GROUP BY priority ORDER BY priority
                """
            )
            rows = []
            for r in cur.fetchall():
                total = r["total"]
                done = r["completed"]
                rows.append({
                    "priority": r["priority"],
                    "total": total,
                    "completed": done,
                    "rate": round(done / total * 100, 1) if total else 0,
                })
        return rows
    finally:
        put_conn(conn)


def owner() -> list:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COALESCE(owner, '未分配') AS owner,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status='completed') AS completed
                FROM todo_tasks GROUP BY owner ORDER BY total DESC
                """
            )
            rows = []
            for r in cur.fetchall():
                total = r["total"]
                done = r["completed"]
                rows.append({
                    "owner": r["owner"],
                    "total": total,
                    "completed": done,
                    "rate": round(done / total * 100, 1) if total else 0,
                })
        return rows
    finally:
        put_conn(conn)


def tags() -> list:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT tag, COUNT(*) AS cnt FROM (
                    SELECT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                    UNION ALL
                    SELECT jsonb_array_elements_text(tags)
                    FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ) t GROUP BY tag ORDER BY cnt DESC
                """
            )
            return [{"tag": r["tag"], "count": r["cnt"]} for r in cur.fetchall()]
    finally:
        put_conn(conn)
