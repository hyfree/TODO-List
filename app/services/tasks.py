"""任务 CRUD 及项目查询服务"""
import json
import logging
from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor, Json

from ..database import get_conn, put_conn
from ..utils import row_to_task, parse_date, new_id, now_iso
from ..config import PRIORITY_MAP

logger = logging.getLogger(__name__)


def load_tasks(filters=None) -> list:
    logger.debug("load_tasks filters=%s", filters)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where, args = [], []
            if filters:
                statuses  = filters.get("status", [])
                priorities = filters.get("priority", [])
                tags      = filters.get("tag", [])
                owners    = filters.get("owner", [])
                projects  = filters.get("project", [])
                completed = filters.get("completed", [None])[0]
                due_from  = filters.get("dueDateFrom", [None])[0]
                due_to    = filters.get("dueDateTo", [None])[0]
                created_from = filters.get("createdAtFrom", [None])[0]
                created_to   = filters.get("createdAtTo", [None])[0]
                search    = filters.get("search", [None])[0]

                if statuses:
                    where.append(f"status IN ({','.join(['%s']*len(statuses))})")
                    args.extend(statuses)
                if priorities:
                    where.append(f"priority IN ({','.join(['%s']*len(priorities))})")
                    args.extend(priorities)
                if tags:
                    tag_clauses = []
                    for t in tags:
                        tag_clauses.append("(tag = %s OR tags @> %s::jsonb)")
                        args.extend([t, json.dumps([t])])
                    where.append("(" + " OR ".join(tag_clauses) + ")")
                if owners:
                    where.append(f"owner IN ({','.join(['%s']*len(owners))})")
                    args.extend(owners)
                if projects:
                    where.append(f"project IN ({','.join(['%s']*len(projects))})")
                    args.extend(projects)
                if completed is not None:
                    where.append("completed = %s")
                    args.append(completed.lower() == "true")
                if due_from:
                    where.append("due_date >= %s"); args.append(parse_date(due_from))
                if due_to:
                    where.append("due_date <= %s"); args.append(parse_date(due_to))
                if created_from:
                    where.append("created_at >= %s"); args.append(created_from)
                if created_to:
                    where.append("created_at <= %s"); args.append(created_to + "T23:59:59Z")
                if search:
                    q = f"%{search.lower()}%"
                    where.append(
                        "(lower(title) LIKE %s OR lower(summary) LIKE %s"
                        " OR lower(description) LIKE %s OR lower(tag) LIKE %s)"
                    )
                    args.extend([q, q, q, q])

            sql = "SELECT * FROM todo_tasks"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC"
            logger.debug("执行查询: %s | args=%s", sql, args)
            cur.execute(sql, args)
            rows = cur.fetchall()
            logger.info("load_tasks 返回 %d 条记录", len(rows))
            return [row_to_task(r) for r in rows]
    except Exception as e:
        logger.error("load_tasks 查询失败: %s", e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def get_task(task_id) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM todo_tasks WHERE id = %s", (str(task_id),))
            row = cur.fetchone()
            if row is None:
                logger.warning("get_task 未找到任务 id=%s", task_id)
            return row_to_task(row)
    except Exception as e:
        logger.error("get_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def create_task(data) -> dict:
    task = data.get("task", data)
    task_id = task.get("id") or new_id()
    now = datetime.now(timezone.utc)
    priority = PRIORITY_MAP.get(task.get("priority", "P2"), task.get("priority", "P2"))
    logger.info("create_task id=%s title=%s priority=%s", task_id, task.get("title"), priority)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO todo_tasks
                    (id, title, summary, description, detail, owner, priority,
                     tag, tags, status, due_date, start_date, created_at, updated_at,
                     completed, completed_at, metadata, project)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (
                    task_id,
                    task.get("title", ""),
                    task.get("summary"),
                    task.get("description"),
                    task.get("detail"),
                    task.get("owner", "wangcai"),
                    priority,
                    task.get("tag"),
                    Json(task.get("tags") or []),
                    task.get("status", "pending"),
                    parse_date(task.get("dueDate") or task.get("due_date")),
                    parse_date(task.get("startDate") or task.get("start_date")),
                    now, now,
                    bool(task.get("completed", False)),
                    None,
                    Json(task.get("metadata") or {}),
                    task.get("project"),
                ),
            )
            conn.commit()
            result = row_to_task(cur.fetchone())
            logger.info("create_task 成功 id=%s", task_id)
            return result
    except Exception as e:
        logger.error("create_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def update_task(task_id, data) -> dict | None:
    updated = data.get("task", data)
    logger.info("update_task id=%s fields=%s", task_id, list(updated.keys()))
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM todo_tasks WHERE id = %s", (str(task_id),))
            existing = cur.fetchone()
            if not existing:
                logger.warning("update_task 未找到任务 id=%s", task_id)
                return None

            sets, args = [], []
            field_map = {
                "title": "title", "summary": "summary",
                "description": "description", "detail": "detail",
                "owner": "owner", "priority": "priority",
                "tag": "tag", "status": "status", "completed": "completed",
                "project": "project",
            }
            for api_key, db_key in field_map.items():
                if api_key in updated:
                    val = updated[api_key]
                    if api_key == "priority":
                        val = PRIORITY_MAP.get(val, val)
                    sets.append(f"{db_key} = %s"); args.append(val)

            if "tags" in updated:
                sets.append("tags = %s"); args.append(Json(updated["tags"] or []))
            if "dueDate" in updated or "due_date" in updated:
                sets.append("due_date = %s")
                args.append(parse_date(updated.get("dueDate") or updated.get("due_date")))
            if "startDate" in updated or "start_date" in updated:
                sets.append("start_date = %s")
                args.append(parse_date(updated.get("startDate") or updated.get("start_date")))

            status = updated.get("status", existing["status"])
            completed = updated.get("completed", existing["completed"])
            if status == "completed":
                completed = True
            elif status in ("pending", "progress", "cancelled"):
                completed = False
            if completed and status != "completed":
                status = "completed"

            set_keys = [s.split(" =")[0].strip() for s in sets]
            if "status" not in set_keys:
                sets.append("status = %s"); args.append(status)
            if "completed" not in set_keys:
                sets.append("completed = %s"); args.append(completed)

            sets.append("updated_at = %s"); args.append(datetime.now(timezone.utc))
            args.append(str(task_id))

            cur.execute(
                f"UPDATE todo_tasks SET {', '.join(sets)} WHERE id = %s RETURNING *",
                args,
            )
            conn.commit()
            result = row_to_task(cur.fetchone())
            logger.info("update_task 成功 id=%s", task_id)
            return result
    except Exception as e:
        logger.error("update_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def delete_task(task_id) -> bool:
    logger.info("delete_task id=%s", task_id)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM todo_tasks WHERE id = %s", (str(task_id),))
            deleted = cur.rowcount > 0
            conn.commit()
        if deleted:
            logger.info("delete_task 成功 id=%s", task_id)
        else:
            logger.warning("delete_task 未找到任务 id=%s", task_id)
        return deleted
    except Exception as e:
        logger.error("delete_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        put_conn(conn)


def set_status(task_id, status):
    return update_task(task_id, {"task": {"status": status}})


def get_all_tags() -> list:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                UNION
                SELECT DISTINCT jsonb_array_elements_text(tags)
                FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ORDER BY 1
                """
            )
            return [r[0] for r in cur.fetchall() if r[0]]
    finally:
        put_conn(conn)


def get_all_owners() -> list:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT owner FROM todo_tasks
                WHERE owner IS NOT NULL AND owner != ''
                ORDER BY owner
                """
            )
            return [r[0] for r in cur.fetchall() if r[0]]
    finally:
        put_conn(conn)


def get_all_projects() -> list:
    """返回所有项目列表，含任务数统计"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(project, '') AS project,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status NOT IN ('completed', 'cancelled')) AS active
                FROM todo_tasks
                GROUP BY project
                ORDER BY total DESC
                """
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def search_tasks(q) -> list:
    q_lower = q.lower()
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM todo_tasks
                WHERE lower(title) LIKE %s OR lower(summary) LIKE %s
                   OR lower(description) LIKE %s OR lower(detail) LIKE %s
                   OR lower(tag) LIKE %s
                ORDER BY created_at DESC
                """,
                tuple([f"%{q_lower}%"] * 5),
            )
            return [row_to_task(r) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def add_note(task_id, author, text) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            note = {"author": author, "text": text, "createdAt": now_iso()}
            cur.execute(
                """
                UPDATE todo_tasks
                SET notes = COALESCE(notes, '[]'::jsonb) || %s::jsonb,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (json.dumps([note]), datetime.now(timezone.utc), str(task_id)),
            )
            conn.commit()
            return row_to_task(cur.fetchone())
    finally:
        put_conn(conn)
