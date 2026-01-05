<script setup>
import { ref, nextTick, onMounted } from 'vue'

// State
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionId = ref(null)
const claudeStatus = ref(null)
const totalCost = ref(0)
const chatContainer = ref(null)

// Session management
const savedSessions = ref([])
const showSessionPicker = ref(false)
const sessionName = ref('')

// Tool presets for common operations
const toolPresets = [
  { name: 'Full Access', tools: null, desc: 'All tools enabled' },
  { name: 'Read Only', tools: ['Read', 'Glob', 'Grep', 'Bash(ls:*)', 'Bash(cat:*)', 'Bash(head:*)'], desc: 'Can only read files' },
  { name: 'Safe Bash', tools: ['Bash', 'Read', 'Write', 'Edit'], desc: 'Shell + file operations' },
  { name: 'Research', tools: ['Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch'], desc: 'Search and read only' },
]
const selectedPreset = ref(toolPresets[0])

// Check Claude Code status
async function checkStatus() {
  try {
    const res = await fetch('/api/claude/status')
    claudeStatus.value = await res.json()
  } catch (e) {
    claudeStatus.value = { available: false, error: e.message }
  }
}

// Load saved sessions
async function loadSessions() {
  try {
    const res = await fetch('/api/claude/sessions')
    const data = await res.json()
    savedSessions.value = data.sessions || []
  } catch (e) {
    console.error('Failed to load sessions:', e)
  }
}

// Save current session
async function saveCurrentSession() {
  if (!sessionId.value) return

  const name = sessionName.value.trim() || `Session ${new Date().toLocaleString()}`
  const firstMsg = messages.value.find(m => m.role === 'user')?.content || ''

  try {
    await fetch('/api/claude/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        name: name,
        first_message: firstMsg.slice(0, 100)
      })
    })
    sessionName.value = name
    await loadSessions()
  } catch (e) {
    console.error('Failed to save session:', e)
  }
}

// Load a saved session
async function loadSession(session) {
  sessionId.value = session.session_id
  sessionName.value = session.name
  messages.value = []
  totalCost.value = 0
  showSessionPicker.value = false

  // Add a system message indicating we resumed
  messages.value.push({
    role: 'assistant',
    content: `📂 Resumed session: "${session.name}"\n\nOriginal prompt: ${session.first_message || '(none saved)'}\n\nYou can continue the conversation - Claude will remember the context.`,
    isSystem: true
  })
}

// Delete a saved session
async function deleteSession(session, event) {
  event.stopPropagation()
  if (!confirm(`Delete session "${session.name}"?`)) return

  try {
    await fetch(`/api/claude/sessions/${session.session_id}`, { method: 'DELETE' })
    await loadSessions()
  } catch (e) {
    console.error('Failed to delete session:', e)
  }
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
  messages.value.push({ role: 'assistant', content: '', loading: true })
  await scrollToBottom()

  isLoading.value = true

  try {
    const payload = {
      message: userMessage,
      session_id: sessionId.value,
      allowed_tools: selectedPreset.value.tools
    }

    const res = await fetch('/api/claude/chat', {
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
    lastMsg.cost = data.cost_usd

    // Track session and cost
    const isNewSession = !sessionId.value && data.session_id
    if (data.session_id) {
      sessionId.value = data.session_id
    }
    totalCost.value += data.cost_usd || 0

    // Auto-save new sessions
    if (isNewSession) {
      await saveCurrentSession()
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
  sessionId.value = null
  sessionName.value = ''
  totalCost.value = 0
}

function formatDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatCost(usd) {
  if (!usd) return ''
  return `$${usd.toFixed(4)}`
}

onMounted(() => {
  checkStatus()
  loadSessions()
})
</script>

<template>
  <div class="agent-chat">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <h2 class="text-lg font-semibold">Claude Code Agent</h2>
        <div v-if="claudeStatus" class="status-indicator">
          <span v-if="claudeStatus.available" class="status-dot online"></span>
          <span v-else class="status-dot offline"></span>
          <span class="text-xs text-gray-400">
            {{ claudeStatus.available ? claudeStatus.version : 'Offline' }}
          </span>
        </div>
      </div>
      <div class="header-right">
        <div class="cost-display" v-if="totalCost > 0">
          Session: {{ formatCost(totalCost) }}
        </div>
        <button @click="showSessionPicker = !showSessionPicker" class="btn-sessions" title="Load saved session">
          📂 Sessions
          <span v-if="savedSessions.length" class="session-count">{{ savedSessions.length }}</span>
        </button>
        <select v-model="selectedPreset" class="preset-select">
          <option v-for="p in toolPresets" :key="p.name" :value="p">{{ p.name }}</option>
        </select>
        <button @click="clearChat" class="btn-clear" title="New chat">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Preset description -->
    <div class="preset-info">
      <span class="text-xs text-gray-500">{{ selectedPreset.desc }}</span>
      <div v-if="sessionId" class="session-info">
        <input
          v-model="sessionName"
          @blur="saveCurrentSession"
          @keydown.enter="$event.target.blur()"
          class="session-name-input"
          placeholder="Name this session..."
        />
        <span class="session-id">{{ sessionId.slice(0, 8) }}</span>
      </div>
    </div>

    <!-- Session Picker -->
    <div v-if="showSessionPicker" class="session-picker">
      <div class="session-picker-header">
        <span>Saved Sessions</span>
        <button @click="showSessionPicker = false" class="close-btn">×</button>
      </div>
      <div v-if="savedSessions.length === 0" class="no-sessions">
        No saved sessions yet. Start a chat to create one.
      </div>
      <div v-else class="session-list">
        <div
          v-for="session in savedSessions"
          :key="session.session_id"
          @click="loadSession(session)"
          class="session-item"
          :class="{ active: session.session_id === sessionId }"
        >
          <div class="session-item-main">
            <div class="session-item-name">{{ session.name }}</div>
            <div class="session-item-preview">{{ session.first_message || '(no preview)' }}</div>
          </div>
          <div class="session-item-meta">
            <span class="session-item-time">{{ formatRelativeTime(session.updated_at) }}</span>
            <button @click="deleteSession(session, $event)" class="session-delete-btn" title="Delete">×</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div ref="chatContainer" class="messages-container">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">🤖</div>
        <div class="empty-title">Claude Code Agent</div>
        <div class="empty-desc">
          Send commands to Claude Code running on DGX.<br>
          It has full access to manage the system.
        </div>
        <div class="example-prompts">
          <button @click="inputMessage = 'What containers are running?'" class="example-btn">
            What containers are running?
          </button>
          <button @click="inputMessage = 'Show GPU and memory usage'" class="example-btn">
            Show GPU and memory usage
          </button>
          <button @click="inputMessage = 'List files in ~/video-generation/'" class="example-btn">
            List files in ~/video-generation/
          </button>
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <div class="message-content">
          <div v-if="msg.loading" class="loading-indicator">
            <div class="typing-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="text-xs text-gray-500 ml-2">Thinking...</span>
          </div>
          <div v-else class="message-text" :class="{ 'error': msg.isError }">
            <pre>{{ msg.content }}</pre>
          </div>
          <div v-if="msg.role === 'assistant' && !msg.loading && (msg.duration || msg.cost)" class="message-meta">
            <span v-if="msg.duration">{{ formatDuration(msg.duration) }}</span>
            <span v-if="msg.cost">{{ formatCost(msg.cost) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-container">
      <textarea
        v-model="inputMessage"
        @keydown.enter.exact.prevent="sendMessage"
        placeholder="Send a command to Claude Code..."
        rows="2"
        class="message-input"
        :disabled="isLoading"
      ></textarea>
      <button
        @click="sendMessage"
        :disabled="isLoading || !inputMessage.trim()"
        class="send-button"
      >
        <span v-if="isLoading">...</span>
        <span v-else>Send</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.agent-chat {
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

.cost-display {
  font-size: 12px;
  color: #9ca3af;
  background: #374151;
  padding: 4px 10px;
  border-radius: 6px;
}

.preset-select {
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

.preset-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  background: #111827;
  border-bottom: 1px solid #374151;
}

.session-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-name-input {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 12px;
  color: #93c5fd;
  width: 150px;
}

.session-name-input:hover {
  border-color: #374151;
}

.session-name-input:focus {
  outline: none;
  border-color: #3b82f6;
  background: #1e3a5f;
}

.session-id {
  font-size: 10px;
  color: #6b7280;
  font-family: monospace;
}

.btn-sessions {
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

.btn-sessions:hover {
  background: #4b5563;
}

.session-count {
  background: #3b82f6;
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
}

.session-picker {
  background: #111827;
  border-bottom: 1px solid #374151;
  max-height: 300px;
  overflow-y: auto;
}

.session-picker-header {
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

.no-sessions {
  padding: 24px 20px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}

.session-list {
  padding: 8px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: #1f2937;
}

.session-item.active {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
}

.session-item-main {
  flex: 1;
  min-width: 0;
}

.session-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #e5e7eb;
  margin-bottom: 4px;
}

.session-item-preview {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}

.session-item-time {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
}

.session-delete-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-delete-btn {
  opacity: 1;
}

.session-delete-btn:hover {
  color: #ef4444;
}

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
  background: #2563eb;
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
  font-size: 14px;
  resize: none;
}

.message-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.message-input:disabled {
  opacity: 0.5;
}

.send-button {
  background: #2563eb;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #1d4ed8;
}

.send-button:disabled {
  background: #4b5563;
  cursor: not-allowed;
}
</style>
