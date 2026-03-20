"""统计路由"""
import asyncio
from fastapi import APIRouter
from ..services import stats as svc
from ..response import ok

router = APIRouter()


@router.get("/api/stats/overview")
async def api_stats_overview():
    return ok({"success": True, "data": await asyncio.to_thread(svc.overview)})


@router.get("/api/stats/trend")
async def api_stats_trend():
    return ok({"success": True, "data": await asyncio.to_thread(svc.trend)})


@router.get("/api/stats/priority")
async def api_stats_priority():
    return ok({"success": True, "data": await asyncio.to_thread(svc.priority)})


@router.get("/api/stats/owner")
async def api_stats_owner():
    return ok({"success": True, "data": await asyncio.to_thread(svc.owner)})


@router.get("/api/stats/tags")
async def api_stats_tags():
    return ok({"success": True, "data": await asyncio.to_thread(svc.tags)})
