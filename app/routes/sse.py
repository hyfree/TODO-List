"""SSE 实时推送路由"""
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from .. import sse as sse_mgr

router = APIRouter()


@router.get("/api/events")
async def sse_stream():
    q = sse_mgr.new_queue()
    await sse_mgr.add_queue(q)

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
            await sse_mgr.remove_queue(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
