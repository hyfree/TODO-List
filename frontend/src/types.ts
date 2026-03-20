export interface Task {
  id: string
  title: string
  summary?: string
  description?: string
  project?: string
  owner?: string
  priority?: string
  status?: string
  tag?: string
  tags?: string[]
  dueDate?: string
  startDate?: string
  createdAt?: string
  updatedAt?: string
  completedAt?: string
  completed?: boolean
}

export interface TaskListResponse {
  success: boolean
  tasks: Task[]
}

export interface ProjectInfo {
  project: string   // '' 表示未分项目
  total: number
  active: number
  completed: number
}

export interface ProjectListResponse {
  success: boolean
  projects: ProjectInfo[]
}
