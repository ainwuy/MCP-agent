<script setup>
import { ref, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false, // 禁用 HTML 以防止 XSS
  linkify: true,
  breaks: true
})

const messages = ref([
  { role: 'ai', content: '你好！我是 MCP 智能助手，可以帮你查询天气、写文件或规划出行路线。' }
])
const userInput = ref('')
const isLoading = ref(false)
const loadingStatus = ref('')
const chatContainer = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  const content = userInput.value.trim()
  if (!content || isLoading.value) return

  // 1. 添加用户消息
  messages.value.push({ role: 'user', content })
  userInput.value = ''
  isLoading.value = true
  loadingStatus.value = '正在思考...'
  await scrollToBottom()

  // 2. 准备 AI 消息占位
  const aiMessage = { role: 'ai', content: '' }
  messages.value.push(aiMessage)

  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content })
    })

    const data = await response.json()
    
    if (data.status === 'success') {
       aiMessage.content = data.content
    } else if (data.status === 'empty') {
       aiMessage.content = '(未获取到回复，请重试)'
    } else {
       aiMessage.content = `[系统错误: ${data.error || '未知错误'}]`
    }

  } catch (e) {
    aiMessage.content = `[网络请求出错: ${e.message}]`
  } finally {
    isLoading.value = false
    loadingStatus.value = ''
    scrollToBottom()
  }
}

const renderMarkdown = (text) => {
  return md.render(text || '')
}
</script>

<template>
  <div class="chat-wrapper">
    <div class="chat-container">
      <!-- 顶部栏 -->
      <div class="chat-header">
        <div class="header-content">
          <div class="status-dot"></div>
          <h2>MCP 智能助手</h2>
        </div>
        <div class="header-subtitle">Powered by Qwen & MCP</div>
      </div>
      
      <!-- 消息列表 -->
      <div class="messages" ref="chatContainer">
        <div v-for="(msg, index) in messages" :key="index" :class="['message-row', msg.role]">
          <div class="avatar">
            <span v-if="msg.role === 'ai'">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M4 11a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-7z"/><path d="M9 16a2 2 0 1 0 4 0 2 2 0 1 0-4 0"/><path d="M15 7v2"/><path d="M9 7v2"/></svg>
            </span>
            <span v-else>
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </span>
          </div>
          <div class="message-bubble">
            <div v-if="msg.role === 'ai'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
            <div v-else>{{ msg.content }}</div>
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-if="isLoading" class="loading-indicator">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
          <span>{{ loadingStatus }}</span>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-box">
          <input 
            v-model="userInput" 
            @keyup.enter="sendMessage"
            placeholder="输入你的问题..." 
            :disabled="isLoading"
          />
          <button @click="sendMessage" :disabled="isLoading || !userInput.trim()" class="send-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 整体容器 */
.chat-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
  /* 浅色网格背景 */
  background-image: 
    linear-gradient(rgba(14, 165, 233, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14, 165, 233, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: center center;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 850px;
  width: 100%;
  max-width: 950px;
  /* 浅色玻璃拟态：高亮白底 + 模糊 */
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.08), /* 柔和的阴影 */
    0 0 0 1px rgba(255, 255, 255, 0.5) inset; /* 内发光增强质感 */
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}

/* 顶部装饰线 - 保留但变浅 */
.chat-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  opacity: 1;
}

/* 头部样式 */
.chat-header {
  padding: 20px 28px;
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #10b981; /* 绿色代表在线，更友好 */
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; transform: scale(0.95); }
  50% { opacity: 1; transform: scale(1.05); }
  100% { opacity: 0.6; transform: scale(0.95); }
}

.chat-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b; /* 深灰黑 */
  letter-spacing: -0.5px;
  font-family: 'Inter', sans-serif;
}

.header-subtitle {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 600;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 20px; /* 圆润标签 */
  border: 1px solid #e2e8f0;
}

/* 消息列表区域 */
.messages {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* 滚动条样式 - 浅色适配 */
.messages::-webkit-scrollbar {
  width: 6px;
}
.messages::-webkit-scrollbar-track {
  background: transparent;
}
.messages::-webkit-scrollbar-thumb {
  background: rgba(203, 213, 225, 0.8);
  border-radius: 3px;
}
.messages::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.8);
}

.message-row {
  display: flex;
  gap: 16px;
  max-width: 85%;
  animation: fadeIn 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-row.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #fff;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.message-row.ai .avatar {
  background: #fff;
  color: #0ea5e9;
  border: 1px solid #e0f2fe;
}

.message-row.user .avatar {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
}

.message-bubble {
  padding: 16px 20px;
  border-radius: 16px;
  font-size: 1rem;
  line-height: 1.65;
  position: relative;
  word-break: break-word;
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}

.message-row.ai .message-bubble {
  background: #ffffff;
  border: 1px solid #f1f5f9;
  color: #334155;
  border-top-left-radius: 4px;
}

.message-row.user .message-bubble {
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
  color: #ffffff;
  border-top-right-radius: 4px;
  box-shadow: 0 8px 16px -4px rgba(14, 165, 233, 0.3); /* 更柔和的彩色阴影 */
}

/* Loading 状态 */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  margin-left: 56px;
  color: #64748b;
  font-size: 0.85rem;
  font-family: monospace;
  background: rgba(255,255,255,0.5);
  border-radius: 20px;
  width: fit-content;
}

.dot {
  width: 6px;
  height: 6px;
  background: #38bdf8;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

/* 输入区域 */
.input-area {
  padding: 24px 32px;
  background: rgba(255, 255, 255, 0.9);
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.input-box {
  display: flex;
  gap: 12px;
  background: #f8fafc;
  padding: 8px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
}

.input-box:focus-within {
  background: #fff;
  border-color: #38bdf8;
  box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.15), 0 4px 12px rgba(0,0,0,0.05);
}

input {
  flex: 1;
  background: transparent;
  border: none;
  padding: 12px 16px;
  color: #1e293b;
  font-size: 1rem;
  outline: none;
}

input::placeholder {
  color: #94a3b8;
}

.send-btn {
  background: #0ea5e9;
  border: none;
  color: white;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(14, 165, 233, 0.2);
}

.send-btn:hover:not(:disabled) {
  background: #0284c7;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.send-btn:disabled {
  background: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

/* Markdown 样式适配浅色模式 */
:deep(.markdown-body) {
  color: #334155;
  font-size: 1rem;
  line-height: 1.7;
}

:deep(.markdown-body p) {
  margin-bottom: 0.8em;
}

:deep(.markdown-body a) {
  color: #0284c7;
  text-decoration: none;
  font-weight: 500;
}

:deep(.markdown-body code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em;
  color: #0f172a;
  border: 1px solid #e2e8f0;
}

:deep(.markdown-body pre) {
  background: #1e293b; /* 代码块保持深色，对比度高 */
  padding: 20px;
  border-radius: 12px;
  overflow-x: auto;
  border: 1px solid #334155;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

:deep(.markdown-body pre code) {
  background: transparent;
  color: #e2e8f0;
  border: none;
  padding: 0;
}
</style>
