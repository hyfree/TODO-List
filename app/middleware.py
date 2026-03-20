"""认证与请求日志中间件"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from .services import tokens as token_svc

logger = logging.getLogger(__name__)


async def auth_middleware(request: Request, call_next):
    """Bearer Token 认证，免认证路径直通"""
    if not token_svc.is_public(request.url.path, request.method):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.query_params.get("api_token")
        if not token:
            return JSONResponse(
                {"success": False, "error": "未授权，请提供 Bearer Token"},
                status_code=401,
            )
        owner = await asyncio.to_thread(token_svc.verify, token)
        if not owner:
            return JSONResponse(
                {"success": False, "error": "Token 无效、已过期或已撤销"},
                status_code=401,
            )
        request.state.owner = owner
    return await call_next(request)


async def request_logger(request: Request, call_next):
    """请求/响应日志，记录耗时"""
    start = datetime.now(timezone.utc)
    logger.info("→ %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.info(
            "← %s %s %d (%.1fms)",
            request.method, request.url.path, response.status_code, elapsed,
        )
        return response
    except Exception as e:
        logger.error("请求异常 %s %s: %s", request.method, request.url.path, e, exc_info=True)
        raise
