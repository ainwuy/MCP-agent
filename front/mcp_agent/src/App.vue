<script setup>
import ChatBox from './components/ChatBox.vue'
</script>

<template>
  <main>
    <ChatBox />
  </main>
</template>

<style>
/* 重置一些基础样式 */
body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  background: #f8fafc; /* 改回清爽的浅色背景 */
  color: #1e293b;
}

#app {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100vw;
  /* 浅色科技风背景：淡蓝灰渐变 */
  background: radial-gradient(circle at 50% 0%, #f1f5f9 0%, #e2e8f0 100%);
}
</style>
