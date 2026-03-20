import { defineStore } from 'pinia'
import { createTask, fetchTasks } from '../api'
import type { Task } from '../types'

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    items: [] as Task[],
    loading: false,
    error: '',
  }),
  actions: {
    async load(project: string) {
      this.loading = true
      this.error = ''
      try {
        const data = await fetchTasks(project)
        this.items = data.tasks || []
      } catch (e) {
        this.error = e instanceof Error ? e.message : '加载失败'
      } finally {
        this.loading = false
      }
    },
    async add(input: {
      title: string
      description?: string
      project?: string
      owner?: string
      priority?: string
    }) {
      await createTask(input)
      await this.load(input.project || '')
    },
  },
})
