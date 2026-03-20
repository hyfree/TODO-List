"""API Token 管理与认证"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from psycopg2.extras import RealDictCursor

from ..database import get_conn, put_conn
from ..utils import fmt_ts

logger = logging.getLogger(__name__)

_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/skill"}


def is_public(path: str, method: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    if path == "/api/tokens" and method == "POST":
        return True
    if not path.startswith("/api/"):
        return True
    if path == "/api/events":
        return True
    return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(owner: str, expires_in_days: Optional[int] = None) -> dict:
    raw = secrets.token_urlsafe(32)
    token_hash = hash_token(raw)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        if expires_in_days
        else None
    )
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO todo_api_tokens (token_hash, owner, expires_at)
                VALUES (%s, %s, %s) RETURNING id, owner, created_at, expires_at, is_active
                """,
                (token_hash, owner, expires_at),
            )
            conn.commit()
            row = dict(cur.fetchone())
            row["token"] = raw  # 仅创建时返回明文
            row["created_at"] = fmt_ts(row["created_at"])
            row["expires_at"] = fmt_ts(row["expires_at"])
            return row
    finally:
        put_conn(conn)


def list_for_owner(owner: str) -> list:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, owner, created_at, expires_at, is_active
                FROM todo_api_tokens WHERE owner = %s ORDER BY created_at DESC
                """,
                (owner,),
            )
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d["created_at"] = fmt_ts(d["created_at"])
                d["expires_at"] = fmt_ts(d["expires_at"])
                rows.append(d)
            return rows
    finally:
        put_conn(conn)


def revoke(token_id: int) -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE todo_api_tokens SET is_active = FALSE WHERE id = %s", (token_id,)
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        put_conn(conn)


def verify(raw: str) -> Optional[str]:
    """验证 token，返回 owner 或 None"""
    token_hash = hash_token(raw)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT owner, expires_at, is_active FROM todo_api_tokens
                WHERE token_hash = %s
                """,
                (token_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            if not row["is_active"]:
                return None
            if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
                return None
            return row["owner"]
    finally:
        put_conn(conn)
