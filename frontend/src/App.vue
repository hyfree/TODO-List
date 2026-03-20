<template>
  <div class="app-shell">
    <header class="topbar">
      <h1 style="margin:0; font-size:17px; font-weight:700">任务指挥中心</h1>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>
