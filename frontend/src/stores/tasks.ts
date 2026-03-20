import { defineStore } from 'pinia'
import { createTask, fetchTasks, updateTask, deleteTask, completeTask } from '../api'
import type { Task } from '../types'

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    items: [] as Task[],
    loading: false,
    error: '',
  }),
  getters: {
    byStatus: (state) => (status: string) =>
      state.items.filter((t) => (t.status || 'pending') === status),
    pendingCount: (state) =>
      state.items.filter((t) => !t.completed && t.status !== 'cancelled').length,
  },
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
      tag?: string
      dueDate?: string
    }) {
      await createTask(input)
      await this.load(input.project || '')
    },
    async update(id: string, payload: Parameters<typeof updateTask>[1]) {
      await updateTask(id, payload)
      const idx = this.items.findIndex((t) => t.id === id)
      if (idx >= 0) {
        this.items[idx] = { ...this.items[idx], ...payload }
      }
    },
    async remove(id: string) {
      await deleteTask(id)
      this.items = this.items.filter((t) => t.id !== id)
    },
    async complete(id: string) {
      await completeTask(id)
      const idx = this.items.findIndex((t) => t.id === id)
      if (idx >= 0) {
        this.items[idx] = { ...this.items[idx], status: 'completed', completed: true }
      }
    },
  },
})
