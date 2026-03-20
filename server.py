#!/usr/bin/env python3
"""
Todo List Server v6.0 - FastAPI
架构：FastAPI + Uvicorn → 数据服务层 → PostgreSQL
与 v5.0 API 完全兼容
"""

import os, json, re, asyncio, logging, traceback, secrets, hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, date, timedelta
from logging.handlers import RotatingFileHandler
from typing import Optional, List

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# ── 日志配置 ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE  = "/home/hyfree/logs/todo-server.log"

def _setup_logging():
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # 控制台
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # 文件（轮转：10MB × 5）
    fh = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

_setup_logging()
logger = logging.getLogger("todo-server")

# ── 数据库配置 ────────────────────────────────────────────────────────────────
DB_CONFIG = dict(
    host="localhost", port=5433, dbname="narrative_db",
    user="postgres", password="postgres_password_change_me"
)
_db_pool = None

def _get_pool():
    global _db_pool
    if _db_pool is None:
        logger.info("初始化数据库连接池 host=%s port=%s db=%s",
                    DB_CONFIG['host'], DB_CONFIG['port'], DB_CONFIG['dbname'])
        try:
            _db_pool = pool.ThreadedConnectionPool(2, 10, **DB_CONFIG)
            logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error("数据库连接池初始化失败: %s", e, exc_info=True)
            raise
    return _db_pool

def _get_conn():
    try:
        conn = _get_pool().getconn()
        logger.debug("获取数据库连接")
        return conn
    except Exception as e:
        logger.error("获取数据库连接失败: %s", e, exc_info=True)
        raise

def _put_conn(conn):
    _get_pool().putconn(conn)
    logger.debug("归还数据库连接")

# ── SSE 客户端管理 ────────────────────────────────────────────────────────────
_sse_queues: List[asyncio.Queue] = []
_sse_lock = asyncio.Lock()

async def _sse_broadcast(event_type: str, task_id=None):
    msg = f"data: {json.dumps({'type': event_type, 'taskId': task_id, 'ts': _now_iso()}, ensure_ascii=False)}\n\n"
    async with _sse_lock:
        dead = []
        for q in _sse_queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _sse_queues.remove(q)

# ── 配置 ──────────────────────────────────────────────────────────────────────
HTML_FILE = "/home/hyfree/todo/todo-pro-kanban-v3.3.html"
PRIORITY_MAP = {"high": "P0", "medium": "P1", "low": "P2"}

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

def _fmt_date(d):
    if d is None:
        return None
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]

def _fmt_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(ts)

def _row_to_task(row):
    if row is None:
        return None
    t = dict(row)
    t['dueDate']     = _fmt_date(t.pop('due_date', None))
    t['startDate']   = _fmt_date(t.pop('start_date', None))
    t['createdAt']   = _fmt_ts(t.pop('created_at', None))
    t['updatedAt']   = _fmt_ts(t.pop('updated_at', None))
    t['completedAt'] = _fmt_ts(t.pop('completed_at', None))
    for field in ('tags', 'metadata', 'notes'):
        val = t.get(field)
        default = [] if field != 'metadata' else {}
        if isinstance(val, str):
            try:
                t[field] = json.loads(val)
            except Exception:
                t[field] = default
        elif val is None:
            t[field] = default
    for k in ['dueDate', 'startDate', 'completedAt', 'summary', 'description', 'detail']:
        if t.get(k) is None:
            t.pop(k, None)
    return t

def _init_token_table():
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS todo_api_tokens (
                    id SERIAL PRIMARY KEY,
                    token_hash VARCHAR(64) NOT NULL UNIQUE,
                    owner VARCHAR(100) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """)
            conn.commit()
            logger.info("todo_api_tokens 表初始化完成")
    except Exception as e:
        logger.error("初始化 token 表失败: %s", e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def token_create(owner: str, expires_in_days: Optional[int] = None):
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days) if expires_in_days else None
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO todo_api_tokens (token_hash, owner, expires_at)
                VALUES (%s, %s, %s) RETURNING id, owner, created_at, expires_at, is_active
            """, (token_hash, owner, expires_at))
            conn.commit()
            row = dict(cur.fetchone())
            row['token'] = raw  # 只在创建时返回明文
            row['created_at'] = _fmt_ts(row['created_at'])
            row['expires_at'] = _fmt_ts(row['expires_at'])
            return row
    finally:
        _put_conn(conn)

def token_list(owner: str):
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, owner, created_at, expires_at, is_active
                FROM todo_api_tokens WHERE owner = %s ORDER BY created_at DESC
            """, (owner,))
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d['created_at'] = _fmt_ts(d['created_at'])
                d['expires_at'] = _fmt_ts(d['expires_at'])
                rows.append(d)
            return rows
    finally:
        _put_conn(conn)

def token_revoke(token_id: int):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE todo_api_tokens SET is_active = FALSE WHERE id = %s", (token_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        _put_conn(conn)

def token_verify(raw: str) -> Optional[str]:
    """验证 token，返回 owner 或 None"""
    token_hash = _hash_token(raw)
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT owner, expires_at, is_active FROM todo_api_tokens
                WHERE token_hash = %s
            """, (token_hash,))
            row = cur.fetchone()
            if not row:
                return None
            if not row['is_active']:
                return None
            if row['expires_at'] and row['expires_at'] < datetime.now(timezone.utc):
                return None
            return row['owner']
    finally:
        _put_conn(conn)

# 免认证路径集合
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

def _is_public(path: str, method: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    # POST /api/tokens 免认证（创建 token）
    if path == "/api/tokens" and method == "POST":
        return True
    # 静态页面
    if not path.startswith("/api/"):
        return True
    # SSE 暂时免认证（EventSource 不支持自定义 header）
    if path == "/api/events":
        return True
    return False

def _new_id():
    date_str = datetime.now().strftime("%Y%m%d")
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM todo_tasks WHERE id LIKE %s ORDER BY id DESC LIMIT 1",
                (f"task-{date_str}-%",)
            )
            row = cur.fetchone()
            seq = 1
            if row:
                m = re.search(r'-(\d+)$', row[0])
                seq = int(m.group(1)) + 1 if m else 1
        return f"task-{date_str}-{seq:03d}"
    finally:
        _put_conn(conn)

# ── 数据服务层（同步，在线程池中运行）────────────────────────────────────────

def load_tasks(filters=None):
    logger.debug("load_tasks filters=%s", filters)
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where, args = [], []
            if filters:
                statuses   = filters.get('status', [])
                priorities = filters.get('priority', [])
                tags       = filters.get('tag', [])
                owners     = filters.get('owner', [])
                completed  = filters.get('completed', [None])[0]
                due_from   = filters.get('dueDateFrom', [None])[0]
                due_to     = filters.get('dueDateTo', [None])[0]
                created_from = filters.get('createdAtFrom', [None])[0]
                created_to   = filters.get('createdAtTo', [None])[0]
                search     = filters.get('search', [None])[0]

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
                if completed is not None:
                    where.append("completed = %s")
                    args.append(completed.lower() == 'true')
                if due_from:
                    where.append("due_date >= %s"); args.append(_parse_date(due_from))
                if due_to:
                    where.append("due_date <= %s"); args.append(_parse_date(due_to))
                if created_from:
                    where.append("created_at >= %s"); args.append(created_from)
                if created_to:
                    where.append("created_at <= %s"); args.append(created_to + 'T23:59:59Z')
                if search:
                    q = f"%{search.lower()}%"
                    where.append("(lower(title) LIKE %s OR lower(summary) LIKE %s OR lower(description) LIKE %s OR lower(tag) LIKE %s)")
                    args.extend([q, q, q, q])

            sql = "SELECT * FROM todo_tasks"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC"
            logger.debug("执行查询: %s | args=%s", sql, args)
            cur.execute(sql, args)
            rows = cur.fetchall()
            logger.info("load_tasks 返回 %d 条记录", len(rows))
            return [_row_to_task(r) for r in rows]
    except Exception as e:
        logger.error("load_tasks 查询失败: %s", e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def get_task(task_id):
    logger.debug("get_task id=%s", task_id)
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM todo_tasks WHERE id = %s", (str(task_id),))
            row = cur.fetchone()
            if row is None:
                logger.warning("get_task 未找到任务 id=%s", task_id)
            return _row_to_task(row)
    except Exception as e:
        logger.error("get_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def create_task(data):
    task = data.get('task', data)
    task_id = task.get('id') or _new_id()
    now = datetime.now(timezone.utc)
    priority = PRIORITY_MAP.get(task.get('priority', 'P2'), task.get('priority', 'P2'))
    logger.info("create_task id=%s title=%s priority=%s", task_id, task.get('title'), priority)

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO todo_tasks
                    (id, title, summary, description, detail, owner, priority,
                     tag, tags, status, due_date, start_date, created_at, updated_at,
                     completed, completed_at, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
            """, (
                task_id,
                task.get('title', ''),
                task.get('summary'),
                task.get('description'),
                task.get('detail'),
                task.get('owner', 'wangcai'),
                priority,
                task.get('tag'),
                Json(task.get('tags') or []),
                task.get('status', 'pending'),
                _parse_date(task.get('dueDate') or task.get('due_date')),
                _parse_date(task.get('startDate') or task.get('start_date')),
                now, now,
                bool(task.get('completed', False)),
                None,
                Json(task.get('metadata') or {}),
            ))
            conn.commit()
            result = _row_to_task(cur.fetchone())
            logger.info("create_task 成功 id=%s", task_id)
            return result
    except Exception as e:
        logger.error("create_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def update_task(task_id, data):
    updated = data.get('task', data)
    logger.info("update_task id=%s fields=%s", task_id, list(updated.keys()))
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM todo_tasks WHERE id = %s", (str(task_id),))
            existing = cur.fetchone()
            if not existing:
                logger.warning("update_task 未找到任务 id=%s", task_id)
                return None

            sets, args = [], []
            field_map = {
                'title': 'title', 'summary': 'summary',
                'description': 'description', 'detail': 'detail',
                'owner': 'owner', 'priority': 'priority',
                'tag': 'tag', 'status': 'status', 'completed': 'completed',
            }
            for api_key, db_key in field_map.items():
                if api_key in updated:
                    val = updated[api_key]
                    if api_key == 'priority':
                        val = PRIORITY_MAP.get(val, val)
                    sets.append(f"{db_key} = %s"); args.append(val)

            if 'tags' in updated:
                sets.append("tags = %s"); args.append(Json(updated['tags'] or []))
            if 'dueDate' in updated or 'due_date' in updated:
                sets.append("due_date = %s")
                args.append(_parse_date(updated.get('dueDate') or updated.get('due_date')))
            if 'startDate' in updated or 'start_date' in updated:
                sets.append("start_date = %s")
                args.append(_parse_date(updated.get('startDate') or updated.get('start_date')))

            status = updated.get('status', existing['status'])
            completed = updated.get('completed', existing['completed'])
            if status == 'completed':
                completed = True
            elif status in ('pending', 'progress', 'cancelled'):
                completed = False
            if completed and status != 'completed':
                status = 'completed'

            set_keys = [s.split(' =')[0].strip() for s in sets]
            if 'status' not in set_keys:
                sets.append("status = %s"); args.append(status)
            if 'completed' not in set_keys:
                sets.append("completed = %s"); args.append(completed)

            sets.append("updated_at = %s"); args.append(datetime.now(timezone.utc))
            args.append(str(task_id))

            cur.execute(
                f"UPDATE todo_tasks SET {', '.join(sets)} WHERE id = %s RETURNING *",
                args
            )
            conn.commit()
            result = _row_to_task(cur.fetchone())
            logger.info("update_task 成功 id=%s", task_id)
            return result
    except Exception as e:
        logger.error("update_task 失败 id=%s: %s", task_id, e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def delete_task(task_id):
    logger.info("delete_task id=%s", task_id)
    conn = _get_conn()
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
        _put_conn(conn)

def set_status(task_id, status):
    return update_task(task_id, {'task': {'status': status}})

def get_all_tags():
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                UNION
                SELECT DISTINCT jsonb_array_elements_text(tags) FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ORDER BY 1
            """)
            return [r[0] for r in cur.fetchall() if r[0]]
    finally:
        _put_conn(conn)

def get_all_owners():
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT owner FROM todo_tasks
                WHERE owner IS NOT NULL AND owner != ''
                ORDER BY owner
            """)
            return [r[0] for r in cur.fetchall() if r[0]]
    finally:
        _put_conn(conn)

def stats_overview():
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='completed') AS completed,
                    COUNT(*) FILTER (WHERE status='pending') AS pending,
                    COUNT(*) FILTER (WHERE status='progress') AS progress,
                    COUNT(*) FILTER (WHERE status='cancelled') AS cancelled
                FROM todo_tasks
            """)
            counts = dict(cur.fetchone())

            cur.execute("""
                SELECT priority, COUNT(*) AS cnt
                FROM todo_tasks GROUP BY priority ORDER BY priority
            """)
            priority_dist = {r['priority']: r['cnt'] for r in cur.fetchall()}

            cur.execute("""
                SELECT tag, COUNT(*) AS cnt
                FROM (
                    SELECT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                    UNION ALL
                    SELECT jsonb_array_elements_text(tags) FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ) t GROUP BY tag ORDER BY cnt DESC LIMIT 20
            """)
            tag_dist = {r['tag']: r['cnt'] for r in cur.fetchall()}

        return {**counts, "priority_dist": priority_dist, "tag_dist": tag_dist}
    finally:
        _put_conn(conn)

def stats_trend():
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DATE(completed_at AT TIME ZONE 'Asia/Shanghai') AS day, COUNT(*) AS cnt
                FROM todo_tasks
                WHERE completed_at IS NOT NULL
                  AND completed_at >= NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
            """)
            completed_by_day = {str(r['day']): r['cnt'] for r in cur.fetchall()}

            cur.execute("""
                SELECT DATE(created_at AT TIME ZONE 'Asia/Shanghai') AS day, COUNT(*) AS cnt
                FROM todo_tasks
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day
            """)
            created_by_day = {str(r['day']): r['cnt'] for r in cur.fetchall()}

        return {"completed_by_day": completed_by_day, "created_by_day": created_by_day}
    finally:
        _put_conn(conn)

def stats_priority():
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    priority,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='completed') AS completed
                FROM todo_tasks
                GROUP BY priority ORDER BY priority
            """)
            rows = []
            for r in cur.fetchall():
                total = r['total']
                done = r['completed']
                rows.append({
                    "priority": r['priority'],
                    "total": total,
                    "completed": done,
                    "rate": round(done / total * 100, 1) if total else 0
                })
        return rows
    finally:
        _put_conn(conn)

def stats_owner():
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COALESCE(owner, '未分配') AS owner,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='completed') AS completed
                FROM todo_tasks
                GROUP BY owner ORDER BY total DESC
            """)
            rows = []
            for r in cur.fetchall():
                total = r['total']
                done = r['completed']
                rows.append({
                    "owner": r['owner'],
                    "total": total,
                    "completed": done,
                    "rate": round(done / total * 100, 1) if total else 0
                })
        return rows
    finally:
        _put_conn(conn)

def stats_tags():
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT tag, COUNT(*) AS cnt
                FROM (
                    SELECT tag FROM todo_tasks WHERE tag IS NOT NULL AND tag != ''
                    UNION ALL
                    SELECT jsonb_array_elements_text(tags) FROM todo_tasks WHERE tags IS NOT NULL AND tags != '[]'::jsonb
                ) t GROUP BY tag ORDER BY cnt DESC
            """)
            return [{"tag": r['tag'], "count": r['cnt']} for r in cur.fetchall()]
    finally:
        _put_conn(conn)

def search_tasks(q):
    q_lower = q.lower()
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM todo_tasks
                WHERE lower(title) LIKE %s OR lower(summary) LIKE %s
                   OR lower(description) LIKE %s OR lower(detail) LIKE %s
                   OR lower(tag) LIKE %s
                ORDER BY created_at DESC
            """, tuple([f"%{q_lower}%"] * 5))
            return [_row_to_task(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)

def create_log(operator, action, task_id=None, task_title=None, detail=None):
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO todo_operation_logs (operator, action, task_id, task_title, detail)
                VALUES (%s, %s, %s, %s, %s) RETURNING *
            """, (operator, action, task_id, task_title, Json(detail or {})))
            conn.commit()
            row = cur.fetchone()
            return {
                "id": row["id"],
                "operatedAt": _fmt_ts(row["operated_at"]),
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
        _put_conn(conn)

def list_logs(page=1, page_size=50, operator=None, action=None):
    conn = _get_conn()
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
            args.extend([page_size, (page - 1) * page_size])
            cur.execute(sql, args)
            rows = cur.fetchall()

            count_sql = "SELECT COUNT(*) FROM todo_operation_logs"
            if where:
                count_sql += " WHERE " + " AND ".join(where[:-2] if len(args) > 2 else where)
            cur.execute("SELECT COUNT(*) FROM todo_operation_logs" + (" WHERE " + " AND ".join(where) if where else ""), args[:-2] if args else [])
            total = cur.fetchone()["count"]

            return {
                "total": total,
                "page": page,
                "pageSize": page_size,
                "logs": [{
                    "id": r["id"],
                    "operatedAt": _fmt_ts(r["operated_at"]),
                    "operator": r["operator"],
                    "action": r["action"],
                    "taskId": r["task_id"],
                    "taskTitle": r["task_title"],
                    "detail": r["detail"],
                } for r in rows]
            }
    except Exception as e:
        logger.error("list_logs 失败: %s", e, exc_info=True)
        raise
    finally:
        _put_conn(conn)

def add_note(task_id, author, text):
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("ALTER TABLE todo_tasks ADD COLUMN IF NOT EXISTS notes JSONB DEFAULT '[]'::jsonb")
            note = {"author": author, "text": text, "createdAt": _now_iso()}
            cur.execute("""
                UPDATE todo_tasks
                SET notes = COALESCE(notes, '[]'::jsonb) || %s::jsonb,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
            """, (json.dumps([note]), datetime.now(timezone.utc), str(task_id)))
            conn.commit()
            return _row_to_task(cur.fetchone())
    finally:
        _put_conn(conn)

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(title="Todo List API v6.0")

@app.on_event("startup")
async def startup_event():
    _get_pool()
    await asyncio.to_thread(_init_token_table)
    logger.info("服务启动完成，Token 表已就绪")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not _is_public(request.url.path, request.method):
        # 优先从 Authorization header 取，其次从 query param
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.query_params.get("api_token")
        if not token:
            return JSONResponse({"success": False, "error": "未授权，请提供 Bearer Token"}, status_code=401)
        owner = await asyncio.to_thread(token_verify, token)
        if not owner:
            return JSONResponse({"success": False, "error": "Token 无效、已过期或已撤销"}, status_code=401)
        request.state.owner = owner
    return await call_next(request)

@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = datetime.now(timezone.utc)
    logger.info("→ %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.info("← %s %s %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed)
        return response
    except Exception as e:
        logger.error("请求异常 %s %s: %s", request.method, request.url.path, e, exc_info=True)
        raise

def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def ok(data: dict, status_code: int = 200):
    import json as _json
    return JSONResponse(content=_json.loads(_json.dumps(data, default=_json_default)), status_code=status_code)

# ── 健康检查 ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return ok({"status": "ok", "service": "todo-api", "version": "6.0"})

# ── Token 管理 ────────────────────────────────────────────────────────────────

@app.post("/api/tokens")
async def create_token(request: Request):
    data = await request.json()
    owner = data.get("owner", "").strip()
    if not owner:
        return ok({"success": False, "error": "owner 不能为空"}, 400)
    expires_in_days = data.get("expires_in_days")
    result = await asyncio.to_thread(token_create, owner, expires_in_days)
    return ok({"success": True, "token": result}, 201)

@app.get("/api/tokens")
async def list_tokens(request: Request, owner: str = Query(default="")):
    q_owner = owner or getattr(request.state, "owner", "")
    if not q_owner:
        return ok({"success": False, "error": "需要指定 owner"}, 400)
    tokens = await asyncio.to_thread(token_list, q_owner)
    return ok({"success": True, "tokens": tokens})

@app.delete("/api/tokens/{token_id}")
async def revoke_token(token_id: int):
    ok_flag = await asyncio.to_thread(token_revoke, token_id)
    if ok_flag:
        return ok({"success": True})
    return ok({"success": False, "error": "Token 不存在"}, 404)

# ── SSE ───────────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def sse_stream():
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    async with _sse_lock:
        _sse_queues.append(q)

    async def generator():
        yield ": connected\n\n"
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with _sse_lock:
                if q in _sse_queues:
                    _sse_queues.remove(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

# ── GET ───────────────────────────────────────────────────────────────────────

@app.get("/api/todos")
async def get_todos():
    tasks = await asyncio.to_thread(load_tasks)
    return ok({"success": True, "tasks": tasks})

@app.get("/api/tasks/search")
async def search(q: str = Query(default="")):
    tasks = await asyncio.to_thread(search_tasks, q)
    return ok({"success": True, "tasks": tasks})

@app.get("/api/stats/overview")
async def api_stats_overview():
    return ok({"success": True, "data": await asyncio.to_thread(stats_overview)})

@app.get("/api/stats/trend")
async def api_stats_trend():
    return ok({"success": True, "data": await asyncio.to_thread(stats_trend)})

@app.get("/api/stats/priority")
async def api_stats_priority():
    return ok({"success": True, "data": await asyncio.to_thread(stats_priority)})

@app.get("/api/stats/owner")
async def api_stats_owner():
    return ok({"success": True, "data": await asyncio.to_thread(stats_owner)})

@app.get("/api/stats/tags")
async def api_stats_tags():
    return ok({"success": True, "data": await asyncio.to_thread(stats_tags)})

@app.get("/api/tasks/tags")
async def tags():
    return ok({"success": True, "tags": await asyncio.to_thread(get_all_tags)})

@app.get("/api/tasks/owners")
async def owners():
    return ok({"success": True, "owners": await asyncio.to_thread(get_all_owners)})

@app.get("/api/tasks/{task_id}")
async def get_one(task_id: str):
    task = await asyncio.to_thread(get_task, task_id)
    if task:
        return ok({"success": True, "task": task})
    return ok({"success": False, "error": "任务不存在"}, 404)

@app.get("/api/tasks")
async def get_tasks(request: Request):
    params = dict(request.query_params)
    # 转成多值 dict 格式与原版兼容
    from urllib.parse import parse_qs
    filters = parse_qs(str(request.url.query)) if request.url.query else None
    tasks = await asyncio.to_thread(load_tasks, filters)
    return ok({"success": True, "tasks": tasks})

@app.get("/api/logs")
async def get_logs(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
    operator: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
):
    result = await asyncio.to_thread(list_logs, page, pageSize, operator, action)
    return ok({"success": True, **result})

@app.get("/")
@app.get("/{full_path:path}")
async def serve_html(full_path: str = ""):
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return ok({"service": "Todo API v6.0", "status": "ok"})

# ── POST ──────────────────────────────────────────────────────────────────────

@app.post("/api/logs")
async def post_log(request: Request):
    data = await request.json()
    log = await asyncio.to_thread(
        create_log,
        data.get("operator", "unknown"),
        data.get("action", "unknown"),
        data.get("taskId"),
        data.get("taskTitle"),
        data.get("detail"),
    )
    return ok({"success": True, "log": log})

@app.post("/api/todos")
async def create_todo(request: Request):
    data = await request.json()
    task = await asyncio.to_thread(create_task, data)
    await _sse_broadcast('create', task.get('id'))
    return ok({"success": True, "task": task})

@app.post("/api/todos/complete")
async def complete_todo(request: Request):
    data = await request.json()
    result = await asyncio.to_thread(set_status, str(data.get('id', '')), 'completed')
    if result:
        await _sse_broadcast('update', result.get('id'))
    return ok({"success": bool(result)})

@app.post("/api/tasks")
async def create_task_endpoint(request: Request):
    data = await request.json()
    task = await asyncio.to_thread(create_task, data)
    await _sse_broadcast('create', task.get('id'))
    return ok({"success": True, "task": task}, 201)

@app.post("/api/tasks/batch")
async def batch_create(request: Request):
    data = await request.json()
    created = []
    for t in data.get('tasks', []):
        task = await asyncio.to_thread(create_task, {'task': t})
        await _sse_broadcast('create', task.get('id'))
        created.append(task)
    return ok({"success": True, "tasks": created})

@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    result = await asyncio.to_thread(set_status, task_id, 'completed')
    if result:
        await _sse_broadcast('update', task_id)
    return ok({"success": bool(result), "task": result})

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    result = await asyncio.to_thread(set_status, task_id, 'cancelled')
    if result:
        await _sse_broadcast('update', task_id)
    return ok({"success": bool(result), "task": result})

@app.post("/api/tasks/{task_id}/notes")
async def add_task_note(task_id: str, request: Request):
    data = await request.json()
    author = data.get('author', 'wangcai')
    text = data.get('text', '').strip()
    if not text:
        return ok({"success": False, "error": "备注内容不能为空"}, 400)
    result = await asyncio.to_thread(add_note, task_id, author, text)
    if result:
        await _sse_broadcast('update', task_id)
        return ok({"success": True, "task": result})
    return ok({"success": False, "error": "任务不存在"}, 404)

# ── PUT ───────────────────────────────────────────────────────────────────────

@app.put("/api/todos/{task_id}")
async def update_todo(task_id: str, request: Request):
    data = await request.json()
    try:
        task_id = str(int(float(task_id)))
    except Exception:
        pass
    result = await asyncio.to_thread(update_task, task_id, data)
    if result:
        await _sse_broadcast('update', task_id)
    return ok({"success": bool(result), "task": result})

@app.put("/api/tasks/{task_id}")
async def update_task_endpoint(task_id: str, request: Request):
    data = await request.json()
    result = await asyncio.to_thread(update_task, task_id, data)
    if result:
        await _sse_broadcast('update', task_id)
        return ok({"success": True, "task": result})
    return ok({"success": False, "error": "任务不存在"}, 404)

# ── DELETE ────────────────────────────────────────────────────────────────────

@app.delete("/api/todos/{task_id}")
async def delete_todo(task_id: str):
    try:
        task_id = str(int(float(task_id)))
    except Exception:
        pass
    ok_flag = await asyncio.to_thread(delete_task, task_id)
    if ok_flag:
        await _sse_broadcast('delete', task_id)
    return ok({"success": ok_flag})

@app.delete("/api/tasks/batch")
async def batch_delete(request: Request):
    data = await request.json()
    deleted = []
    for i in data.get('ids', []):
        if await asyncio.to_thread(delete_task, str(i)):
            await _sse_broadcast('delete', str(i))
            deleted.append(i)
    return ok({"success": True, "deleted": deleted})

@app.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    ok_flag = await asyncio.to_thread(delete_task, task_id)
    if ok_flag:
        await _sse_broadcast('delete', task_id)
        return ok({"success": True})
    return ok({"success": False, "error": "任务不存在"}, 404)

# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    _get_pool()
    _init_token_table()
    import uvicorn
    print("🚀 Todo List Server v6.0 (FastAPI) 启动")
    print(f"   DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print("   API: http://0.0.0.0:5003/api/tasks")
    uvicorn.run(app, host="0.0.0.0", port=5003, log_level="info")
