<template>
  <nav class="project-nav">
    <div class="project-nav__header">
      <span class="project-nav__title">项目</span>
      <button class="project-nav__refresh" :disabled="loading" @click="projectStore.loadProjects()" title="刷新">
        ↻
      </button>
    </div>

    <!-- 全部项目 -->
    <button
      class="project-nav__item"
      :class="{ active: currentProject === '' }"
      @click="select('')"
    >
      <span class="project-nav__name">全部项目</span>
      <span v-if="projectStore.totalAll > 0" class="project-nav__badge">
        {{ projectStore.activeAll }}
      </span>
    </button>

    <!-- 各项目 -->
    <button
      v-for="p in projects"
      :key="p.project"
      class="project-nav__item"
      :class="{ active: currentProject === p.project }"
      @click="select(p.project)"
    >
      <span class="project-nav__name">{{ p.project || '(未分配)' }}</span>
      <span v-if="p.active > 0" class="project-nav__badge">{{ p.active }}</span>
    </button>

    <p v-if="!loading && projects.length === 0" class="project-nav__empty">暂无项目</p>
  </nav>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useProjectStore } from '../stores/project'

const projectStore = useProjectStore()

const loading = computed(() => projectStore.loading)
const currentProject = computed(() => projectStore.currentProject)
const projects = computed(() => projectStore.projects.filter((p) => p.project !== ''))

onMounted(() => {
  if (projectStore.projects.length === 0) {
    projectStore.loadProjects()
  }
})

function select(project: string) {
  projectStore.setProject(project)
}
</script>
