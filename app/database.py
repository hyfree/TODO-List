"""数据库连接池管理"""
import logging
from psycopg2 import pool
from .config import DB_CONFIG

logger = logging.getLogger(__name__)

_db_pool = None


def get_pool():
    global _db_pool
    if _db_pool is None:
        logger.info(
            "初始化数据库连接池 host=%s port=%s db=%s",
            DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"],
        )
        try:
            _db_pool = pool.ThreadedConnectionPool(2, 10, **DB_CONFIG)
            logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error("数据库连接池初始化失败: %s", e, exc_info=True)
            raise
    return _db_pool


def get_conn():
    try:
        conn = get_pool().getconn()
        logger.debug("获取数据库连接")
        return conn
    except Exception as e:
        logger.error("获取数据库连接失败: %s", e, exc_info=True)
        raise


def put_conn(conn):
    get_pool().putconn(conn)
    logger.debug("归还数据库连接")


def ensure_schema():
    """确保数据库 schema 完整（幂等）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # API Token 表
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
            # project 列（新增/已有均安全）
            cur.execute("""
                ALTER TABLE todo_tasks ADD COLUMN IF NOT EXISTS project VARCHAR(200)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_todo_tasks_project ON todo_tasks(project)
            """)
            # notes 列
            cur.execute("""
                ALTER TABLE todo_tasks ADD COLUMN IF NOT EXISTS notes JSONB DEFAULT '[]'::jsonb
            """)
            conn.commit()
            logger.info("数据库 schema 检查完成")
    except Exception as e:
        logger.error("schema 确认失败: %s", e, exc_info=True)
        conn.rollback()
        raise
    finally:
        put_conn(conn)
