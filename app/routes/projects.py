"""项目路由（新增）"""
import asyncio
from fastapi import APIRouter
from ..services import tasks as svc
from ..response import ok

router = APIRouter()


@router.get("/api/projects")
async def list_projects():
    """返回所有项目及任务数统计"""
    projects = await asyncio.to_thread(svc.get_all_projects)
    return ok({"success": True, "projects": projects})
