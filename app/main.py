"""FastAPI 应用工厂"""
import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import HTML_FILE
from .database import get_pool, ensure_schema
from .middleware import auth_middleware, request_logger
from .routes import tasks, stats, logs, tokens, sse, projects
from .response import ok

logger = logging.getLogger(__name__)

app = FastAPI(title="Todo List API v6.0")

# ── 中间件（后注册 = 外层，先执行）────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(auth_middleware)
app.middleware("http")(request_logger)

# ── 路由 ──────────────────────────────────────────────────────────────────────
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(logs.router)
app.include_router(tokens.router)
app.include_router(sse.router)
app.include_router(projects.router)


# ── 生命周期 ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    get_pool()
    await asyncio.to_thread(ensure_schema)
    logger.info("服务启动完成，schema 已就绪")


# ── 基础端点 ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return ok({"status": "ok", "service": "todo-api", "version": "6.0"})


@app.get("/skill")
async def get_skill():
    """返回 SKILL.md 内容，供 Copilot Agent 加载"""
    skill_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        ".github", "skills", "todo-api", "SKILL.md",
    )
    if os.path.exists(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f"<pre>{f.read()}</pre>")
    return ok({"error": "SKILL.md 未找到"}, 404)


@app.get("/")
@app.get("/{full_path:path}")
async def serve_html(full_path: str = ""):
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return ok({"service": "Todo API v6.0", "status": "ok"})

