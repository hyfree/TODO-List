"""操作日志服务"""
import logging
from psycopg2.extras import RealDictCursor, Json
from ..database import get_conn, put_conn
from ..utils import fmt_ts

logger = logging.getLogger(__name__)


def create(operator, action, task_id=None, task_title=None, detail=None) -> dict:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO todo_operation_logs (operator, action, task_id, task_title, detail)
                VALUES (%s, %s, %s, %s, %s) RETURNING *
                """,
                (operator, action, task_id, task_title, Json(detail or {})),
            )
            conn.commit()
            row = cur.fetchone()
            return {
                "id": row["id"],
                "operatedAt": fmt_ts(row["operated_at"]),
                "operator": row["operator"],
                "action": row["action"],
                "taskId": row["task_id"],
                "taskTitle": row["task_title"],
                "detail": row["detail"],
            }
    except Exception as e:
        logger.error("create_log 失败: %s", e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def list_logs(page=1, page_size=50, operator=None, action=None) -> dict:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where, args = [], []
            if operator:
                where.append("operator = %s"); args.append(operator)
            if action:
                where.append("action = %s"); args.append(action)

            sql = "SELECT * FROM todo_operation_logs"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY operated_at DESC LIMIT %s OFFSET %s"
            cur.execute(sql, args + [page_size, (page - 1) * page_size])
            rows = cur.fetchall()

            count_sql = "SELECT COUNT(*) FROM todo_operation_logs"
            if where:
                count_sql += " WHERE " + " AND ".join(where)
            cur.execute(count_sql, args)
            total = cur.fetchone()["count"]

            return {
                "total": total,
                "page": page,
                "pageSize": page_size,
                "logs": [
                    {
                        "id": r["id"],
                        "operatedAt": fmt_ts(r["operated_at"]),
                        "operator": r["operator"],
                        "action": r["action"],
                        "taskId": r["task_id"],
                        "taskTitle": r["task_title"],
                        "detail": r["detail"],
                    }
                    for r in rows
                ],
            }
    except Exception as e:
        logger.error("list_logs 失败: %s", e, exc_info=True)
        raise
    finally:
        put_conn(conn)
