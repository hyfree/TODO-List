"""任务相关路由"""
import asyncio
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Query

from ..services import tasks as svc
from ..sse import broadcast
from ..response import ok

router = APIRouter()


@router.get("/api/todos")
async def get_todos(request: Request):
    filters = parse_qs(str(request.url.query)) if request.url.query else None
    tasks = await asyncio.to_thread(svc.load_tasks, filters)
    return ok({"success": True, "tasks": tasks})


@router.get("/api/tasks/search")
async def search(q: str = Query(default="")):
    tasks = await asyncio.to_thread(svc.search_tasks, q)
    return ok({"success": True, "tasks": tasks})


@router.get("/api/tasks/tags")
async def tags():
    return ok({"success": True, "tags": await asyncio.to_thread(svc.get_all_tags)})


@router.get("/api/tasks/owners")
async def owners():
    return ok({"success": True, "owners": await asyncio.to_thread(svc.get_all_owners)})


@router.get("/api/tasks/{task_id}")
async def get_one(task_id: str):
    task = await asyncio.to_thread(svc.get_task, task_id)
    if task:
        return ok({"success": True, "task": task})
    return ok({"success": False, "error": "任务不存在"}, 404)


@router.get("/api/tasks")
async def get_tasks(request: Request):
    filters = parse_qs(str(request.url.query)) if request.url.query else None
    tasks = await asyncio.to_thread(svc.load_tasks, filters)
    return ok({"success": True, "tasks": tasks})


@router.post("/api/todos")
async def create_todo(request: Request):
    data = await request.json()
    task = await asyncio.to_thread(svc.create_task, data)
    await broadcast("create", task.get("id"))
    return ok({"success": True, "task": task})


@router.post("/api/todos/complete")
async def complete_todo(request: Request):
    data = await request.json()
    result = await asyncio.to_thread(svc.set_status, str(data.get("id", "")), "completed")
    if result:
        await broadcast("update", result.get("id"))
    return ok({"success": bool(result)})


@router.post("/api/tasks")
async def create_task_endpoint(request: Request):
    data = await request.json()
    task = await asyncio.to_thread(svc.create_task, data)
    await broadcast("create", task.get("id"))
    return ok({"success": True, "task": task}, 201)


@router.post("/api/tasks/batch")
async def batch_create(request: Request):
    data = await request.json()
    created = []
    for t in data.get("tasks", []):
        task = await asyncio.to_thread(svc.create_task, {"task": t})
        await broadcast("create", task.get("id"))
        created.append(task)
    return ok({"success": True, "tasks": created})


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    result = await asyncio.to_thread(svc.set_status, task_id, "completed")
    if result:
        await broadcast("update", task_id)
    return ok({"success": bool(result), "task": result})


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    result = await asyncio.to_thread(svc.set_status, task_id, "cancelled")
    if result:
        await broadcast("update", task_id)
    return ok({"success": bool(result), "task": result})


@router.post("/api/tasks/{task_id}/notes")
async def add_task_note(task_id: str, request: Request):
    data = await request.json()
    author = data.get("author", "wangcai")
    text = data.get("text", "").strip()
    if not text:
        return ok({"success": False, "error": "备注内容不能为空"}, 400)
    result = await asyncio.to_thread(svc.add_note, task_id, author, text)
    if result:
        await broadcast("update", task_id)
        return ok({"success": True, "task": result})
    return ok({"success": False, "error": "任务不存在"}, 404)


@router.put("/api/todos/{task_id}")
async def update_todo(task_id: str, request: Request):
    data = await request.json()
    try:
        task_id = str(int(float(task_id)))
    except Exception:
        pass
    result = await asyncio.to_thread(svc.update_task, task_id, data)
    if result:
        await broadcast("update", task_id)
    return ok({"success": bool(result), "task": result})


@router.put("/api/tasks/{task_id}")
async def update_task_endpoint(task_id: str, request: Request):
    data = await request.json()
    result = await asyncio.to_thread(svc.update_task, task_id, data)
    if result:
        await broadcast("update", task_id)
        return ok({"success": True, "task": result})
    return ok({"success": False, "error": "任务不存在"}, 404)


@router.delete("/api/todos/{task_id}")
async def delete_todo(task_id: str):
    try:
        task_id = str(int(float(task_id)))
    except Exception:
        pass
    ok_flag = await asyncio.to_thread(svc.delete_task, task_id)
    if ok_flag:
        await broadcast("delete", task_id)
    return ok({"success": ok_flag})


@router.delete("/api/tasks/batch")
async def batch_delete(request: Request):
    data = await request.json()
    deleted = []
    for i in data.get("ids", []):
        if await asyncio.to_thread(svc.delete_task, str(i)):
            await broadcast("delete", str(i))
            deleted.append(i)
    return ok({"success": True, "deleted": deleted})


@router.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    ok_flag = await asyncio.to_thread(svc.delete_task, task_id)
    if ok_flag:
        await broadcast("delete", task_id)
        return ok({"success": True})
    return ok({"success": False, "error": "任务不存在"}, 404)
