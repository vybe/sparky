<script setup>
import { ref, nextTick, onMounted } from 'vue'

// State
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const gooseStatus = ref(null)
const chatContainer = ref(null)

// Research files management
const savedResearch = ref([])
const showResearchPanel = ref(false)
const selectedResearch = ref(null)

// Mode: 'chat' for quick queries, 'research' for full research agent
const researchMode = ref('chat')
const modes = [
  { id: 'chat', name: 'Quick Chat', desc: 'Fast Q&A with web search' },
  { id: 'research', name: 'Deep Research', desc: 'Full research with saved notes' },
]

// Check Goose status
async function checkStatus() {
  try {
    const res = await fetch('/api/goose/status')
    gooseStatus.value = await res.json()
  } catch (e) {
    gooseStatus.value = { available: false, error: e.message }
  }
}

// Load saved research files
async function loadResearch() {
  try {
    const res = await fetch('/api/goose/research')
    const data = await res.json()
    savedResearch.value = data.files || []
  } catch (e) {
    console.error('Failed to load research:', e)
  }
}

// View a research file
async function viewResearch(file) {
  try {
    const res = await fetch(`/api/goose/research/${encodeURIComponent(file.name)}`)
    const data = await res.json()
    selectedResearch.value = { ...file, content: data.content }
  } catch (e) {
    console.error('Failed to load research file:', e)
  }
}

// Delete a research file
async function deleteResearch(file, event) {
  event.stopPropagation()
  if (!confirm(`Delete "${file.name}"?`)) return

  try {
    await fetch(`/api/goose/research/${encodeURIComponent(file.name)}`, { method: 'DELETE' })
    await loadResearch()
    if (selectedResearch.value?.name === file.name) {
      selectedResearch.value = null
    }
  } catch (e) {
    console.error('Failed to delete research:', e)
  }
}

// Format file size
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format relative time
function formatRelativeTime(isoDate) {
  const date = new Date(isoDate)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Send message
async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // Add user message
  messages.value.push({ role: 'user', content: userMessage })

  // Add placeholder for assistant
  messages.value.push({ role: 'assistant', content: '', loading: true, sources: [] })
  await scrollToBottom()

  isLoading.value = true

  try {
    const payload = {
      message: userMessage,
      mode: researchMode.value
    }

    const res = await fetch('/api/goose/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Request failed')
    }

    const data = await res.json()

    // Update assistant message
    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.loading = false
    lastMsg.content = data.result
    lastMsg.duration = data.duration_ms
    lastMsg.sources = data.sources || []
    lastMsg.saved_file = data.saved_file

    // Refresh research files if something was saved
    if (data.saved_file) {
      await loadResearch()
    }

    await scrollToBottom()

  } catch (e) {
    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.loading = false
    lastMsg.content = `Error: ${e.message}`
    lastMsg.isError = true
  } finally {
    isLoading.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function clearChat() {
  messages.value = []
  selectedResearch.value = null
}

function formatDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

// Insert research topic into input
function insertTopic(topic) {
  inputMessage.value = topic
}

// Safely extract hostname from URL
function getHostname(url) {
  try {
    return new URL(url).hostname
  } catch {
    // If URL is malformed, just show a truncated version
    return url.length > 30 ? url.slice(0, 30) + '...' : url
  }
}

onMounted(() => {
  checkStatus()
  loadResearch()
})
</script>

<template>
  <div class="goose-chat">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <h2 class="text-lg font-semibold">Goose Research Agent</h2>
        <div v-if="gooseStatus" class="status-indicator">
          <span v-if="gooseStatus.available" class="status-dot online"></span>
          <span v-else class="status-dot offline"></span>
          <span class="text-xs text-gray-400">
            {{ gooseStatus.available ? gooseStatus.version : 'Offline' }}
          </span>
        </div>
      </div>
      <div class="header-right">
        <button @click="showResearchPanel = !showResearchPanel" class="btn-research" title="View saved research">
          📚 Research
          <span v-if="savedResearch.length" class="research-count">{{ savedResearch.length }}</span>
        </button>
        <select v-model="researchMode" class="mode-select">
          <option v-for="m in modes" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
        <button @click="clearChat" class="btn-clear" title="New chat">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Mode description -->
    <div class="mode-info">
      <span class="text-xs text-gray-500">{{ modes.find(m => m.id === researchMode)?.desc }}</span>
      <span class="text-xs text-gray-600">Model: qwen3:30b-a3b</span>
    </div>

    <!-- Research Panel -->
    <div v-if="showResearchPanel" class="research-panel">
      <div class="research-panel-header">
        <span>Saved Research</span>
        <button @click="showResearchPanel = false" class="close-btn">×</button>
      </div>

      <div class="research-panel-content">
        <!-- File List -->
        <div class="research-list">
          <div v-if="savedResearch.length === 0" class="no-research">
            No saved research yet. Use "Deep Research" mode to save findings.
          </div>
          <div
            v-for="file in savedResearch"
            :key="file.name"
            @click="viewResearch(file)"
            class="research-item"
            :class="{ active: selectedResearch?.name === file.name }"
          >
            <div class="research-item-main">
              <div class="research-item-name">{{ file.name.replace('.md', '') }}</div>
              <div class="research-item-meta">
                <span>{{ formatSize(file.size) }}</span>
                <span>{{ formatRelativeTime(file.modified) }}</span>
              </div>
            </div>
            <button @click="deleteResearch(file, $event)" class="research-delete-btn" title="Delete">×</button>
          </div>
        </div>

        <!-- File Preview -->
        <div v-if="selectedResearch" class="research-preview">
          <div class="research-preview-header">
            <span class="font-medium">{{ selectedResearch.name }}</span>
          </div>
          <div class="research-preview-content">
            <pre>{{ selectedResearch.content }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div ref="chatContainer" class="messages-container">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">🪿</div>
        <div class="empty-title">Goose Research Agent</div>
        <div class="empty-desc">
          Ask questions about any topic. Goose will search the web,<br>
          gather information, and synthesize findings for you.
        </div>
        <div class="example-prompts">
          <button @click="insertTopic('What are the latest developments in AI agents?')" class="example-btn">
            Latest AI agent developments
          </button>
          <button @click="insertTopic('Compare different local LLM frameworks')" class="example-btn">
            Compare local LLM frameworks
          </button>
          <button @click="insertTopic('Research MCP (Model Context Protocol) architecture')" class="example-btn">
            Research MCP architecture
          </button>
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <div class="message-content">
          <div v-if="msg.loading" class="loading-indicator">
            <div class="typing-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="text-xs text-gray-500 ml-2">Researching...</span>
          </div>
          <div v-else class="message-text" :class="{ 'error': msg.isError }">
            <pre>{{ msg.content }}</pre>
          </div>

          <!-- Sources -->
          <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
            <span class="sources-label">Sources:</span>
            <div class="sources-list">
              <a
                v-for="(source, sidx) in msg.sources"
                :key="sidx"
                :href="source"
                target="_blank"
                class="source-link"
              >
                {{ getHostname(source) }}
              </a>
            </div>
          </div>

          <!-- Saved file indicator -->
          <div v-if="msg.saved_file" class="saved-indicator">
            💾 Saved to: {{ msg.saved_file }}
          </div>

          <div v-if="msg.role === 'assistant' && !msg.loading && msg.duration" class="message-meta">
            <span>{{ formatDuration(msg.duration) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-container">
      <textarea
        v-model="inputMessage"
        @keydown.enter.exact.prevent="sendMessage"
        :placeholder="researchMode === 'research' ? 'Enter a research topic...' : 'Ask a question...'"
        rows="2"
        inputmode="text"
        autocomplete="off"
        autocorrect="on"
        autocapitalize="sentences"
        spellcheck="true"
        class="message-input"
        :disabled="isLoading"
      ></textarea>
      <button
        @click="sendMessage"
        :disabled="isLoading || !inputMessage.trim()"
        class="send-button"
      >
        <span v-if="isLoading">...</span>
        <span v-else>{{ researchMode === 'research' ? 'Research' : 'Ask' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.goose-chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 500px;
  background: #1f2937;
  border-radius: 12px;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #111827;
  border-bottom: 1px solid #374151;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: #22c55e;
}

.status-dot.offline {
  background: #ef4444;
}

.mode-select {
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 6px;
  padding: 6px 12px;
  color: white;
  font-size: 13px;
}

.btn-clear {
  background: #374151;
  border: none;
  border-radius: 6px;
  padding: 6px;
  color: #9ca3af;
  cursor: pointer;
}

.btn-clear:hover {
  background: #4b5563;
  color: white;
}

.btn-research {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 6px;
  padding: 6px 12px;
  color: #d1d5db;
  font-size: 13px;
  cursor: pointer;
}

.btn-research:hover {
  background: #4b5563;
}

.research-count {
  background: #10b981;
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
}

.mode-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  background: #111827;
  border-bottom: 1px solid #374151;
}

/* Research Panel */
.research-panel {
  background: #111827;
  border-bottom: 1px solid #374151;
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.research-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #9ca3af;
  border-bottom: 1px solid #374151;
}

.close-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
}

.close-btn:hover {
  color: white;
}

.research-panel-content {
  display: flex;
  flex: 1;
  min-height: 0;
}

.research-list {
  width: 250px;
  border-right: 1px solid #374151;
  overflow-y: auto;
  padding: 8px;
}

.no-research {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

.research-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.research-item:hover {
  background: #1f2937;
}

.research-item.active {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
}

.research-item-main {
  flex: 1;
  min-width: 0;
}

.research-item-name {
  font-size: 13px;
  font-weight: 500;
  color: #e5e7eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.research-item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.research-delete-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.research-item:hover .research-delete-btn {
  opacity: 1;
}

.research-delete-btn:hover {
  color: #ef4444;
}

.research-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.research-preview-header {
  padding: 10px 16px;
  border-bottom: 1px solid #374151;
  color: #d1d5db;
  font-size: 13px;
}

.research-preview-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.research-preview-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
}

/* Messages */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #6b7280;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #9ca3af;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 24px;
}

.example-prompts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.example-btn {
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 8px;
  padding: 10px 16px;
  color: #d1d5db;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.example-btn:hover {
  background: #4b5563;
  border-color: #6b7280;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message-content {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .message-content {
  background: #059669;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #374151;
  border-bottom-left-radius: 4px;
}

.message-text {
  font-size: 14px;
  line-height: 1.5;
}

.message-text pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
}

.message-text.error {
  color: #f87171;
}

.message-sources {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #4b5563;
}

.sources-label {
  font-size: 11px;
  color: #9ca3af;
  display: block;
  margin-bottom: 6px;
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-link {
  font-size: 11px;
  color: #60a5fa;
  background: #1e3a5f;
  padding: 2px 8px;
  border-radius: 4px;
  text-decoration: none;
}

.source-link:hover {
  background: #2563eb;
  color: white;
}

.saved-indicator {
  margin-top: 8px;
  font-size: 11px;
  color: #10b981;
}

.message-meta {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 11px;
  color: #6b7280;
}

.loading-indicator {
  display: flex;
  align-items: center;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background: #6b7280;
  border-radius: 50%;
  animation: typing 1s infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; }
  30% { opacity: 1; }
}

.input-container {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: #111827;
  border-top: 1px solid #374151;
}

.message-input {
  flex: 1;
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 8px;
  padding: 12px 16px;
  color: white;
  font-size: 16px;
  resize: none;
  touch-action: manipulation;
  -webkit-appearance: none;
}

.message-input:focus {
  outline: none;
  border-color: #10b981;
}

.message-input:disabled {
  opacity: 0.5;
}

.send-button {
  background: #059669;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.send-button:hover:not(:disabled) {
  background: #047857;
}

.send-button:disabled {
  background: #4b5563;
  cursor: not-allowed;
}
</style>
