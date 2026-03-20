"""操作日志路由"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Request, Query
from ..services import logs as svc
from ..response import ok

router = APIRouter()


@router.get("/api/logs")
async def get_logs(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
    operator: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
):
    result = await asyncio.to_thread(svc.list_logs, page, pageSize, operator, action)
    return ok({"success": True, **result})


@router.post("/api/logs")
async def post_log(request: Request):
    data = await request.json()
    log = await asyncio.to_thread(
        svc.create,
        data.get("operator", "unknown"),
        data.get("action", "unknown"),
        data.get("taskId"),
        data.get("taskTitle"),
        data.get("detail"),
    )
    return ok({"success": True, "log": log})
