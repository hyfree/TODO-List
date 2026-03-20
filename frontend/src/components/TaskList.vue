<template>
  <div class="panel">
    <div class="task-list__header">
      <h3>
        任务列表
        <span v-if="!loading" class="task-list__count">{{ tasks.length }}</span>
      </h3>
    </div>
    <div v-if="loading" class="task-list__empty">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="tasks.length === 0" class="task-list__empty">暂无任务</div>
    <table v-else class="task-table">
      <thead>
        <tr>
          <th>标题</th>
          <th>项目</th>
          <th>负责人</th>
          <th>优先级</th>
          <th>状态</th>
          <th>截止</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id" :class="rowClass(task)">
          <td class="task-title">
            <span :title="task.description">{{ task.title }}</span>
            <span v-if="task.tag" class="task-tag">{{ task.tag }}</span>
          </td>
          <td>{{ task.project || '—' }}</td>
          <td>{{ task.owner || '—' }}</td>
          <td>
            <span class="priority-badge" :class="`prio-${task.priority}`">
              {{ task.priority || '—' }}
            </span>
          </td>
          <td>
            <span class="status-badge" :class="`status-${task.status}`">
              {{ statusLabel(task.status) }}
            </span>
          </td>
          <td>{{ task.dueDate ? task.dueDate.slice(0, 10) : '—' }}</td>
          <td class="task-actions">
            <button
              v-if="task.status !== 'completed'"
              class="btn-complete"
              title="完成"
              @click="emit('complete', task.id)"
            >✓</button>
            <button class="btn-delete" title="删除" @click="emit('delete', task.id)">✕</button>
          </td>
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

const emit = defineEmits<{
  (e: 'complete', id: string): void
  (e: 'delete', id: string): void
}>()

const statusMap: Record<string, string> = {
  pending: '待处理',
  progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
}

function statusLabel(s?: string) {
  return statusMap[s || 'pending'] ?? s ?? '待处理'
}

function rowClass(task: Task) {
  return {
    'task-row--completed': task.status === 'completed',
    'task-row--cancelled': task.status === 'cancelled',
  }
}
</script>
