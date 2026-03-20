import type { RouteRecordRaw } from 'vue-router'
import TaskBoardPage from './views/TaskBoardPage.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'task-board',
    component: TaskBoardPage,
  },
]
