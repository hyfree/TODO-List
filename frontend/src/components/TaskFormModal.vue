<template>
  <div class="panel">
    <h3>新建任务</h3>
    <form @submit.prevent="submit">
      <input v-model.trim="title" placeholder="任务标题 *" required />
      <input v-model.trim="project" placeholder="项目（可选）" />
      <input v-model.trim="owner" placeholder="负责人（可选）" />
      <input v-model.trim="tag" placeholder="标签（可选）" />
      <div class="form-row">
        <select v-model="priority">
          <option value="P0">P0 紧急</option>
          <option value="P1">P1 高</option>
          <option value="P2">P2 普通</option>
        </select>
        <input v-model.trim="dueDate" type="date" title="截止日期" />
      </div>
      <textarea v-model.trim="description" placeholder="描述（可选）" rows="2" />
      <button type="submit">创建</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ currentProject: string }>()
const emit = defineEmits<{
  (e: 'create', payload: {
    title: string
    project?: string
    owner?: string
    priority?: string
    tag?: string
    dueDate?: string
    description?: string
  }): void
}>()

const title = ref('')
const project = ref('')
const owner = ref('wangcai')
const priority = ref('P1')
const tag = ref('')
const dueDate = ref('')
const description = ref('')

watch(
  () => props.currentProject,
  (v) => { project.value = v || '' },
  { immediate: true },
)

const submit = () => {
  if (!title.value) return
  emit('create', {
    title: title.value,
    project: project.value || undefined,
    owner: owner.value || undefined,
    priority: priority.value,
    tag: tag.value || undefined,
    dueDate: dueDate.value || undefined,
    description: description.value || undefined,
  })
  title.value = ''
  tag.value = ''
  dueDate.value = ''
  description.value = ''
}
</script>
