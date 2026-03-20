import type { TaskListResponse } from './types'

const API_BASE = window.location.origin

export async function fetchTasks(project: string): Promise<TaskListResponse> {
  const query = project ? `?project=${encodeURIComponent(project)}` : ''
  const res = await fetch(`${API_BASE}/api/todos${query}`)
  if (!res.ok) throw new Error(`加载任务失败: ${res.status}`)
  return res.json()
}

export async function createTask(payload: {
  title: string
  description?: string
  project?: string
  owner?: string
  priority?: string
}) {
  const res = await fetch(`${API_BASE}/api/todos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: payload }),
  })
  if (!res.ok) throw new Error(`创建任务失败: ${res.status}`)
  return res.json()
}
