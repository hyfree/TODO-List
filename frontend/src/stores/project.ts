import { defineStore } from 'pinia'

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: '',
    knownProjects: [] as string[],
  }),
  actions: {
    setProject(project: string) {
      this.currentProject = project
    },
    setKnownProjects(projects: string[]) {
      this.knownProjects = projects.filter(Boolean)
    },
  },
})
