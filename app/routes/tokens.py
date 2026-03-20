"""Token 管理路由"""
import asyncio
from fastapi import APIRouter, Request, Query
from ..services import tokens as svc
from ..response import ok

router = APIRouter()


@router.post("/api/tokens")
async def create_token(request: Request):
    data = await request.json()
    owner = data.get("owner", "").strip()
    if not owner:
        return ok({"success": False, "error": "owner 不能为空"}, 400)
    expires_in_days = data.get("expires_in_days")
    result = await asyncio.to_thread(svc.create, owner, expires_in_days)
    return ok({"success": True, "token": result}, 201)


@router.get("/api/tokens")
async def list_tokens(request: Request, owner: str = Query(default="")):
    q_owner = owner or getattr(request.state, "owner", "")
    if not q_owner:
        return ok({"success": False, "error": "需要指定 owner"}, 400)
    tokens = await asyncio.to_thread(svc.list_for_owner, q_owner)
    return ok({"success": True, "tokens": tokens})


@router.delete("/api/tokens/{token_id}")
async def revoke_token(token_id: int):
    ok_flag = await asyncio.to_thread(svc.revoke, token_id)
    if ok_flag:
        return ok({"success": True})
    return ok({"success": False, "error": "Token 不存在"}, 404)
