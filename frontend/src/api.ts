import type { TaskListResponse, ProjectListResponse } from './types'

const API_BASE = window.location.origin

export async function fetchTasks(project: string): Promise<TaskListResponse> {
  const query = project ? `?project=${encodeURIComponent(project)}` : ''
  const res = await fetch(`${API_BASE}/api/todos${query}`)
  if (!res.ok) throw new Error(`加载任务失败: ${res.status}`)
  return res.json()
}

export async function fetchProjects(): Promise<ProjectListResponse> {
  const res = await fetch(`${API_BASE}/api/projects`)
  if (!res.ok) throw new Error(`加载项目失败: ${res.status}`)
  return res.json()
}

export async function createTask(payload: {
  title: string
  description?: string
  project?: string
  owner?: string
  priority?: string
  tag?: string
  dueDate?: string
}) {
  const res = await fetch(`${API_BASE}/api/todos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: payload }),
  })
  if (!res.ok) throw new Error(`创建任务失败: ${res.status}`)
  return res.json()
}

export async function updateTask(
  id: string,
  payload: Partial<{
    title: string
    status: string
    priority: string
    owner: string
    project: string
    description: string
    dueDate: string
  }>,
) {
  const res = await fetch(`${API_BASE}/api/tasks/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: payload }),
  })
  if (!res.ok) throw new Error(`更新任务失败: ${res.status}`)
  return res.json()
}

export async function deleteTask(id: string) {
  const res = await fetch(`${API_BASE}/api/tasks/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`删除任务失败: ${res.status}`)
  return res.json()
}

export async function completeTask(id: string) {
  const res = await fetch(`${API_BASE}/api/tasks/${id}/complete`, { method: 'POST' })
  if (!res.ok) throw new Error(`完成任务失败: ${res.status}`)
  return res.json()
}
