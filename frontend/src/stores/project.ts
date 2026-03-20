import { defineStore } from 'pinia'
import { fetchProjects } from '../api'
import type { ProjectInfo } from '../types'

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: '',
    projects: [] as ProjectInfo[],
    loading: false,
  }),
  getters: {
    knownProjects: (state) => state.projects.map((p) => p.project).filter(Boolean),
    currentInfo: (state) =>
      state.projects.find((p) => p.project === state.currentProject) ?? null,
    totalAll: (state) => state.projects.reduce((s, p) => s + p.total, 0),
    activeAll: (state) => state.projects.reduce((s, p) => s + p.active, 0),
  },
  actions: {
    setProject(project: string) {
      this.currentProject = project
    },
    async loadProjects() {
      this.loading = true
      try {
        const data = await fetchProjects()
        this.projects = data.projects || []
      } catch {
        // 静默失败，保持旧数据
      } finally {
        this.loading = false
      }
      state.projects.find((p) => p.project === state.currentProject) ?? null,
    totalAll: (state) => state.projects.reduce((s, p) => s + p.total, 0),
    activeAll: (state) => state.projects.reduce((s, p) => s + p.active, 0),
  },
  actions: {
    setProject(project: string) {
      this.currentProject = project
    },
    async loadProjects() {
      this.loading = true
      try {
        const data = await fetchProjects()
        this.projects = data.projects || []
      } catch {
        // 静默失败，保持旧数据
      } finally {
        this.loading = false
      }
    },
  },
})
