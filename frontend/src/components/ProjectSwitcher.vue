<template>
  <div class="project-switcher">
    <label>项目</label>
    <select :value="model" @change="onChange">
      <option value="">全部项目</option>
      <option v-for="p in projects" :key="p" :value="p">{{ p }}</option>
    </select>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  model: string
  projects: string[]
}>()
const emit = defineEmits<{ (e: 'update:model', value: string): void }>()

const onChange = (e: Event) => {
  const v = (e.target as HTMLSelectElement).value
  emit('update:model', v)
}
</script>
