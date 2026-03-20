"""SSE 客户端队列管理"""
import asyncio
import json
import logging
from .utils import now_iso

logger = logging.getLogger(__name__)

_queues: list[asyncio.Queue] = []
_lock = asyncio.Lock()


async def broadcast(event_type: str, task_id=None):
    msg = (
        f"data: {json.dumps({'type': event_type, 'taskId': task_id, 'ts': now_iso()}, ensure_ascii=False)}\n\n"
    )
    async with _lock:
        dead = []
        for q in _queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _queues.remove(q)


def new_queue() -> asyncio.Queue:
    return asyncio.Queue(maxsize=50)


async def add_queue(q: asyncio.Queue):
    async with _lock:
        _queues.append(q)


async def remove_queue(q: asyncio.Queue):
    async with _lock:
        if q in _queues:
            _queues.remove(q)
