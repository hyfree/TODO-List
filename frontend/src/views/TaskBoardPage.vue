<template>
  <section class="page">
    <ProjectSwitcher
      :model="projectStore.currentProject"
      :projects="projectStore.knownProjects"
      @update:model="onProjectChange"
    />

    <TaskFormModal
      :current-project="projectStore.currentProject"
      @create="onCreate"
    />

    <TaskList
      :tasks="taskStore.items"
      :loading="taskStore.loading"
      :error="taskStore.error"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ProjectSwitcher from '../components/ProjectSwitcher.vue'
import TaskFormModal from '../components/TaskFormModal.vue'
import TaskList from '../components/TaskList.vue'
import { useProjectStore } from '../stores/project'
import { useTaskStore } from '../stores/tasks'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const taskStore = useTaskStore()

const queryProject = computed(() => String(route.query.project || ''))

const syncFromRoute = async () => {
  projectStore.setProject(queryProject.value)
  await taskStore.load(projectStore.currentProject)
  const projects = Array.from(
    new Set(taskStore.items.map((t) => t.project).filter((v): v is string => !!v)),
  )
  projectStore.setKnownProjects(projects)
}

watch(() => route.query.project, syncFromRoute, { immediate: true })

const onProjectChange = (project: string) => {
  router.replace({ query: project ? { project } : {} })
}

const onCreate = async (payload: {
  title: string
  project?: string
  owner?: string
  priority?: string
  description?: string
}) => {
  await taskStore.add(payload)
  await syncFromRoute()
}
</script>
