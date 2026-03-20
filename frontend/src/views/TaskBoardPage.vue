<template>
  <div class="board">
    <!-- 侧边栏：项目列表 -->
    <aside class="board__sidebar">
      <ProjectSwitcher />
    </aside>

    <!-- 主区域 -->
    <main class="board__main">
      <TaskFormModal
        :current-project="projectStore.currentProject"
        @create="onCreate"
      />
      <TaskList
        :tasks="taskStore.items"
        :loading="taskStore.loading"
        :error="taskStore.error"
        @complete="onComplete"
        @delete="onDelete"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import ProjectSwitcher from '../components/ProjectSwitcher.vue'
import TaskFormModal from '../components/TaskFormModal.vue'
import TaskList from '../components/TaskList.vue'
import { useProjectStore } from '../stores/project'
import { useTaskStore } from '../stores/tasks'

const projectStore = useProjectStore()
const taskStore = useTaskStore()

// 项目切换后重新加载任务
watch(
  () => projectStore.currentProject,
  (project) => taskStore.load(project),
  { immediate: true },
)

// 创建任务后刷新项目列表（新项目可能出现）
const onCreate = async (payload: {
  title: string
  project?: string
  owner?: string
  priority?: string
  tag?: string
  dueDate?: string
  description?: string
}) => {
  await taskStore.add(payload)
  projectStore.loadProjects()
}

const onComplete = (id: string) => taskStore.complete(id)
const onDelete = async (id: string) => {
  await taskStore.remove(id)
  projectStore.loadProjects()
}
</script>
