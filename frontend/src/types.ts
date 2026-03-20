export interface Task {
  id: string
  title: string
  description?: string
  project?: string
  owner?: string
  priority?: string
  status?: string
  createdAt?: string
  updatedAt?: string
}

export interface TaskListResponse {
  success: boolean
  tasks: Task[]
}
