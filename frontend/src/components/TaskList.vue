<template>
  <div class="panel">
    <h3>任务列表</h3>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <table v-else class="task-table">
      <thead>
        <tr>
          <th>标题</th>
          <th>项目</th>
          <th>归属</th>
          <th>优先级</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id">
          <td>{{ task.title }}</td>
          <td>{{ task.project || '—' }}</td>
          <td>{{ task.owner || '—' }}</td>
          <td>{{ task.priority || '—' }}</td>
          <td>{{ task.status || 'pending' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { Task } from '../types'

defineProps<{
  tasks: Task[]
  loading: boolean
  error: string
}>()
</script>
