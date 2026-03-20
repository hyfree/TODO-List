---
name: todo-api
description: 与本地 Todo 任务管理系统交互。当用户要求查询、创建、更新、删除任务、切换项目、进行任务生命周期操作（认领、开始、交付、验收、完成等）、查看统计或操作日志时，使用此 skill。
---

## 服务信息

- **地址**: `http://localhost:5003`
- **认证**: 无需认证，API 完全开放

## 任务数据结构

```json
{
  "id": "task-20260320-001",
  "title": "任务标题",
  "description": "任务详细描述",
  "project": "项目名称",
  "owner": "wangcai",
  "priority": "P1",
  "status": "pending",
  "tag": "工作",
  "tags": [],
  "assignee": null,
  "task_type": "manual",
  "requires_acceptance": true,
  "completed": false,
  "createdAt": "2026-03-20T00:00:00Z",
  "updatedAt": "2026-03-20T00:00:00Z"
}
```

字段说明：
- `priority`：`P0`（紧急）/ `P1`（重要）/ `P2`（普通），也接受 `high`/`medium`/`low`
- `status`：`pending` → `claimed` → `progress` → `delivered` → `accepted` / `rejected` → `completed`
- `owner`：`xianxiaoyu`（闲小鱼）/ `wangcai`（旺财）/ `shared`（共同）
- `project`：自由文本，用于按项目过滤，例如 `todo-web`、`narrative-engine`

## 任务 CRUD

### 获取任务列表

```bash
# 获取所有任务
curl http://localhost:5003/api/todos

# 按项目过滤
curl "http://localhost:5003/api/todos?project=todo-web"

# 按多条件过滤（使用 /api/tasks）
curl "http://localhost:5003/api/tasks?status=pending&priority=P0"
```

响应：`{ "success": true, "tasks": [...] }`

### 获取单个任务

```bash
curl http://localhost:5003/api/tasks/{id}
```

### 创建任务

```bash
curl -X POST http://localhost:5003/api/todos \
  -H "Content-Type: application/json" \
  -d '{
    "task": {
      "title": "任务标题",
      "description": "详细描述",
      "project": "todo-web",
      "priority": "P1",
      "owner": "wangcai",
      "tag": "工作",
      "dueDate": "2026-03-30"
    }
  }'
```

响应：`{ "success": true, "task": {...} }`

### 更新任务

```bash
curl -X PUT http://localhost:5003/api/todos/{id} \
  -H "Content-Type: application/json" \
  -d '{"task": {"title": "新标题", "priority": "P0", "project": "new-project"}}'
```

### 删除任务

```bash
# 单个删除
curl -X DELETE http://localhost:5003/api/tasks/{id}

# 批量删除
curl -X DELETE http://localhost:5003/api/tasks/batch \
  -H "Content-Type: application/json" \
  -d '{"ids": ["id1", "id2"]}'
```

### 搜索任务

```bash
curl "http://localhost:5003/api/tasks/search?q=关键词"
```

## 任务生命周期

状态流转：`pending` → `claimed` → `progress` → `delivered` → `accepted`/`rejected` → `completed`

```bash
# 认领任务（pending → claimed）
curl -X POST http://localhost:5003/api/tasks/{id}/claim

# 开始执行（claimed → progress）
curl -X POST http://localhost:5003/api/tasks/{id}/start

# 提交交付物（progress → delivered）
curl -X POST http://localhost:5003/api/tasks/{id}/deliver \
  -H "Content-Type: application/json" \
  -d '{"deliverable": "交付说明", "detail": "补充信息"}'

# 验收通过（delivered → accepted）
curl -X POST http://localhost:5003/api/tasks/{id}/accept

# 驳回（delivered → rejected）
curl -X POST http://localhost:5003/api/tasks/{id}/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "驳回原因"}'

# 直接完成
curl -X POST http://localhost:5003/api/tasks/{id}/complete

# 取消任务
curl -X POST http://localhost:5003/api/tasks/{id}/cancel
```

## 备注与评论

```bash
# 添加备注
curl -X POST http://localhost:5003/api/tasks/{id}/notes \
  -H "Content-Type: application/json" \
  -d '{"author": "wangcai", "text": "备注内容"}'

# 获取评论
curl http://localhost:5003/api/tasks/{id}/comments

# 添加评论
curl -X POST http://localhost:5003/api/tasks/{id}/comments \
  -H "Content-Type: application/json" \
  -d '{"author": "user", "author_type": "user", "content": "评论内容"}'
```

## 标签与归属

```bash
# 获取所有标签
curl http://localhost:5003/api/tasks/tags

# 获取所有归属人
curl http://localhost:5003/api/tasks/owners
```

## 统计分析

```bash
# 总览统计
curl http://localhost:5003/api/stats/overview

# 优先级分布
curl http://localhost:5003/api/stats/priority

# 归属人分布
curl http://localhost:5003/api/stats/owner

# 标签分布
curl http://localhost:5003/api/stats/tags

# 近30天趋势
curl http://localhost:5003/api/stats/trend
```

## 操作日志

```bash
# 查询日志（支持分页）
curl "http://localhost:5003/api/logs?page=1&pageSize=50"

# 按操作类型过滤：create / update / delete / complete / cancel / move
curl "http://localhost:5003/api/logs?action=create&pageSize=20"

# 写入日志
curl -X POST http://localhost:5003/api/logs \
  -H "Content-Type: application/json" \
  -d '{"operator": "wangcai", "action": "create", "taskId": "task-xxx", "taskTitle": "标题", "detail": {}}'
```

## 实时推送（SSE）

```bash
# 监听任务变更事件
curl -N http://localhost:5003/api/events
```

事件格式：`data: {"type": "create"|"update"|"delete", "taskId": "...", "ts": "..."}`

## 健康检查

```bash
curl http://localhost:5003/health
# 响应：{"status":"ok","service":"todo-api","version":"6.0"}
```

## 操作规范

1. 读取前先用 GET 确认当前状态，避免覆盖冲突
2. 批量操作前先确认 ID 列表正确
3. 生命周期操作须遵循状态流转顺序，不能跳步
4. `project` 字段区分项目，为空则任务归入"全部"
5. 删除含评论的任务时，评论会被级联删除

## SKILL 下载

- **GitHub Raw**: `https://raw.githubusercontent.com/hyfree/TODO-List/main/.github/skills/todo-api/SKILL.md`
- **本地服务**: `http://localhost:5003/skill`
