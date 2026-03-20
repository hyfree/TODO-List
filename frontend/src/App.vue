<template>
  <div class="app-shell">
    <header class="topbar">
      <h1>任务指挥中心</h1>
    </header>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>
