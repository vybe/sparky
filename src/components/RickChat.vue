<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'

// State
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionId = ref(null)
const rickStatus = ref(null)
const totalCost = ref(0)
const chatContainer = ref(null)

// Streaming state
const currentStreamController = ref(null)
const streamingText = ref('')
const currentTool = ref(null)
const lastFailedSessionId = ref(null)

// Session management
const savedSessions = ref([])
const showSessionPicker = ref(false)
const sessionName = ref('')

// File upload state
const pendingFiles = ref([])
const isDragging = ref(false)
const fileInputRef = ref(null)
const isUploading = ref(false)

// Check Rick status
async function checkStatus() {
  try {
    const res = await fetch('/api/rick/status')
    rickStatus.value = await res.json()
  } catch (e) {
    rickStatus.value = { available: false, error: e.message }
  }
}

// Load saved sessions
async function loadSessions() {
  try {
    const res = await fetch('/api/rick/sessions')
    const data = await res.json()
    // Sort by updated_at descending (most recent first)
    const sessions = data.sessions || []
    sessions.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    savedSessions.value = sessions
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
    await fetch('/api/rick/sessions', {
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
    content: `📂 Resumed session: "${session.name}"\n\nOriginal prompt: ${session.first_message || '(none saved)'}\n\nYou can continue the conversation - Rick will remember the context.`,
    isSystem: true
  })
}

// Delete a saved session
async function deleteSession(session, event) {
  event.stopPropagation()
  if (!confirm(`Delete session "${session.name}"?`)) return

  try {
    await fetch(`/api/rick/sessions/${session.session_id}`, { method: 'DELETE' })
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

// Send message with streaming
async function sendMessage() {
  if ((!inputMessage.value.trim() && pendingFiles.value.length === 0) || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // Clear any previous failed session tracking
  lastFailedSessionId.value = null

  // Upload any pending files first
  let uploadedPaths = []
  let fileRefs = ''
  if (pendingFiles.value.length > 0) {
    uploadedPaths = await uploadFiles()
    if (uploadedPaths.length > 0) {
      fileRefs = '\n\n[Attached files: ' + uploadedPaths.join(', ') + ']'
    }
    pendingFiles.value = [] // Clear pending files after upload
  }

  const fullMessage = userMessage + fileRefs

  // Add user message with file indicators
  const userMsgContent = pendingFiles.value.length > 0
    ? userMessage + (uploadedPaths.length > 0 ? ` [${uploadedPaths.length} file(s) attached]` : '')
    : userMessage
  messages.value.push({ role: 'user', content: userMsgContent || '[Files attached]', files: uploadedPaths })

  // Add placeholder for assistant with streaming indicator
  const assistantMsg = {
    role: 'assistant',
    content: '',
    loading: true,
    streaming: true,
    tools: [],
    duration: null,
    cost: null
  }
  messages.value.push(assistantMsg)
  await scrollToBottom()

  isLoading.value = true
  streamingText.value = ''
  currentTool.value = null

  // Create abort controller for cancellation
  const abortController = new AbortController()
  currentStreamController.value = abortController

  try {
    const payload = {
      message: fullMessage || '[See attached files]',
      session_id: sessionId.value,
      files: uploadedPaths
    }

    const res = await fetch('/api/rick/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: abortController.signal
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Request failed')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let receivedSessionId = sessionId.value
    let finalResult = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process SSE events (lines starting with "data: ")
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        const jsonStr = line.slice(6) // Remove "data: " prefix
        if (!jsonStr.trim()) continue

        try {
          const event = JSON.parse(jsonStr)

          // Track session ID as soon as we get it
          if (event.session_id && !receivedSessionId) {
            receivedSessionId = event.session_id
            sessionId.value = event.session_id
          }

          switch (event.type) {
            case 'init':
              // Initial event
              assistantMsg.content = '⏳ ' + (event.message || 'Starting...')
              break

            case 'message':
              // Streaming text content
              streamingText.value += event.text || ''
              assistantMsg.content = streamingText.value
              assistantMsg.loading = false
              await scrollToBottom()
              break

            case 'tool_use':
              // Rick is using a tool
              currentTool.value = event.tool
              if (!assistantMsg.tools.includes(event.tool)) {
                assistantMsg.tools.push(event.tool)
              }
              // Show tool indicator in content
              if (!streamingText.value.includes(`[Using ${event.tool}]`)) {
                streamingText.value += `\n[Using ${event.tool}...]\n`
                assistantMsg.content = streamingText.value
              }
              break

            case 'system':
              // System messages
              if (event.message && !streamingText.value) {
                assistantMsg.content = '💭 ' + event.message
              }
              break

            case 'result':
              // Final result
              finalResult = event
              assistantMsg.content = event.result || streamingText.value
              assistantMsg.duration = event.duration_ms
              assistantMsg.cost = event.cost_usd
              totalCost.value += event.cost_usd || 0
              if (event.session_id) {
                sessionId.value = event.session_id
              }
              break

            case 'error':
              // Error occurred
              assistantMsg.content = `Error: ${event.error}`
              assistantMsg.isError = true
              // Save session ID for potential resume
              if (event.session_id) {
                lastFailedSessionId.value = event.session_id
              }
              break

            case 'done':
              // Stream complete
              assistantMsg.duration = assistantMsg.duration || event.duration_ms
              if (event.session_id) {
                sessionId.value = event.session_id
              }
              break

            case 'cancelled':
              assistantMsg.content += '\n\n[Cancelled]'
              break
          }
        } catch (parseErr) {
          console.warn('Failed to parse SSE event:', jsonStr, parseErr)
        }
      }
    }

    // Finalize message
    assistantMsg.loading = false
    assistantMsg.streaming = false

    // If we got a result, use it; otherwise use accumulated text
    if (finalResult) {
      assistantMsg.content = finalResult.result || streamingText.value || assistantMsg.content
    } else if (streamingText.value) {
      assistantMsg.content = streamingText.value
    }

    // Auto-save new sessions
    const isNewSession = receivedSessionId && receivedSessionId !== sessionId.value
    if (isNewSession || (receivedSessionId && !sessionName.value)) {
      sessionId.value = receivedSessionId
      await saveCurrentSession()
    }

    await scrollToBottom()

  } catch (e) {
    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.loading = false
    lastMsg.streaming = false

    if (e.name === 'AbortError') {
      lastMsg.content = streamingText.value + '\n\n[Cancelled by user]'
    } else {
      lastMsg.content = streamingText.value
        ? `${streamingText.value}\n\n⚠️ Connection error: ${e.message}`
        : `Error: ${e.message}`
      lastMsg.isError = true

      // Save session ID for potential resume
      if (sessionId.value) {
        lastFailedSessionId.value = sessionId.value
      }
    }
  } finally {
    isLoading.value = false
    currentStreamController.value = null
    streamingText.value = ''
    currentTool.value = null
  }
}

// Cancel current streaming request
function cancelStream() {
  if (currentStreamController.value) {
    currentStreamController.value.abort()
  }
}

// Resume last failed session
async function resumeLastSession() {
  const resumeSessionId = lastFailedSessionId.value || sessionId.value
  if (!resumeSessionId) return

  // Set the session and ask what happened
  sessionId.value = resumeSessionId
  inputMessage.value = 'What was the result of the previous task? Please summarize what you did.'
  lastFailedSessionId.value = null
  await sendMessage()
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function clearChat() {
  // Cancel any ongoing stream
  if (currentStreamController.value) {
    currentStreamController.value.abort()
  }
  messages.value = []
  sessionId.value = null
  sessionName.value = ''
  totalCost.value = 0
  lastFailedSessionId.value = null
  streamingText.value = ''
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

// File upload functions
function handleFileSelect(event) {
  const files = event.target.files
  if (files) {
    addFiles(Array.from(files))
  }
  // Reset input so same file can be selected again
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function handleDragOver(event) {
  event.preventDefault()
  isDragging.value = true
}

function handleDragLeave(event) {
  event.preventDefault()
  isDragging.value = false
}

function handleDrop(event) {
  event.preventDefault()
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files) {
    addFiles(Array.from(files))
  }
}

function addFiles(files) {
  // Filter for supported file types
  const supportedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf']
  const validFiles = files.filter(f => supportedTypes.includes(f.type))

  if (validFiles.length < files.length) {
    const rejected = files.length - validFiles.length
    console.warn(`${rejected} file(s) rejected - only images and PDFs are supported`)
  }

  // Add to pending files with preview
  for (const file of validFiles) {
    const fileObj = {
      file,
      name: file.name,
      type: file.type,
      size: file.size,
      preview: null,
      uploaded: false,
      uploadPath: null
    }

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        fileObj.preview = e.target.result
      }
      reader.readAsDataURL(file)
    }

    pendingFiles.value.push(fileObj)
  }
}

function removeFile(index) {
  pendingFiles.value.splice(index, 1)
}

async function uploadFiles() {
  if (pendingFiles.value.length === 0) return []

  isUploading.value = true
  const uploadedPaths = []

  try {
    for (const fileObj of pendingFiles.value) {
      if (fileObj.uploaded && fileObj.uploadPath) {
        uploadedPaths.push(fileObj.uploadPath)
        continue
      }

      const formData = new FormData()
      formData.append('file', fileObj.file)
      formData.append('agent', 'rick')

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      })

      if (res.ok) {
        const data = await res.json()
        fileObj.uploaded = true
        fileObj.uploadPath = data.path
        uploadedPaths.push(data.path)
      } else {
        console.error('Upload failed for', fileObj.name)
      }
    }
  } finally {
    isUploading.value = false
  }

  return uploadedPaths
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

onMounted(() => {
  checkStatus()
  loadSessions()
})

onUnmounted(() => {
  // Cancel any ongoing stream when component unmounts
  if (currentStreamController.value) {
    currentStreamController.value.abort()
  }
})
</script>

<template>
  <div class="rick-chat">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <h2 class="text-lg font-semibold">Rick - Family Assistant</h2>
        <div v-if="rickStatus" class="status-indicator">
          <span v-if="rickStatus.available" class="status-dot online"></span>
          <span v-else class="status-dot offline"></span>
          <span class="text-xs text-gray-400">
            {{ rickStatus.available ? rickStatus.version : 'Offline' }}
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
        <button @click="clearChat" class="btn-clear" title="New chat">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Session info -->
    <div class="preset-info">
      <span class="text-xs text-gray-500">Family Documents & Personal Assistant</span>
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
        <div class="empty-icon">🧑‍💼</div>
        <div class="empty-title">Rick - Family Assistant</div>
        <div class="empty-desc">
          Your personal assistant for family documents,<br>
          personal information, and administrative tasks.
        </div>
        <div class="example-prompts">
          <button @click="inputMessage = 'What documents are expiring soon?'" class="example-btn">
            Documents expiring soon?
          </button>
          <button @click="inputMessage = 'Show my Portuguese NIF number'" class="example-btn">
            Show my NIF number
          </button>
          <button @click="inputMessage = 'What is our current address?'" class="example-btn">
            Current address?
          </button>
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <div class="message-content">
          <div v-if="msg.loading && !msg.content" class="loading-indicator">
            <div class="typing-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="text-xs text-gray-500 ml-2">
              {{ currentTool ? `Using ${currentTool}...` : 'Thinking...' }}
            </span>
          </div>
          <div v-else class="message-text" :class="{ 'error': msg.isError, 'streaming': msg.streaming }">
            <pre>{{ msg.content }}</pre>
            <span v-if="msg.streaming && msg.loading" class="streaming-cursor">▋</span>
          </div>
          <div v-if="msg.role === 'assistant' && !msg.loading" class="message-meta">
            <span v-if="msg.tools && msg.tools.length" class="tools-used">
              🔧 {{ msg.tools.join(', ') }}
            </span>
            <span v-if="msg.duration">{{ formatDuration(msg.duration) }}</span>
            <span v-if="msg.cost">{{ formatCost(msg.cost) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Resume Banner (shown when there's a failed session to resume) -->
    <div v-if="lastFailedSessionId && !isLoading" class="resume-banner">
      <span class="resume-text">⚠️ Previous task may have completed. Want to check the result?</span>
      <button @click="resumeLastSession" class="resume-btn">
        Resume & Check
      </button>
      <button @click="lastFailedSessionId = null" class="dismiss-btn">
        Dismiss
      </button>
    </div>

    <!-- Pending Files Preview -->
    <div v-if="pendingFiles.length > 0" class="pending-files">
      <div class="pending-files-header">
        <span>📎 {{ pendingFiles.length }} file(s) attached</span>
        <button @click="pendingFiles = []" class="clear-files-btn">Clear all</button>
      </div>
      <div class="pending-files-list">
        <div v-for="(file, idx) in pendingFiles" :key="idx" class="pending-file">
          <div class="pending-file-preview">
            <img v-if="file.preview" :src="file.preview" class="file-thumbnail" />
            <div v-else class="file-icon">{{ file.type === 'application/pdf' ? '📄' : '📎' }}</div>
          </div>
          <div class="pending-file-info">
            <div class="pending-file-name">{{ file.name }}</div>
            <div class="pending-file-size">{{ formatFileSize(file.size) }}</div>
          </div>
          <button @click="removeFile(idx)" class="remove-file-btn">×</button>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div
      class="input-container"
      :class="{ 'drag-over': isDragging }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <!-- Hidden file input -->
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*,application/pdf"
        multiple
        @change="handleFileSelect"
        class="hidden-file-input"
      />

      <!-- Drag overlay -->
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-overlay-content">
          <span class="drag-icon">📎</span>
          <span>Drop files here</span>
        </div>
      </div>

      <!-- File attach button -->
      <button
        @click="triggerFileInput"
        class="attach-button"
        :disabled="isLoading"
        title="Attach image or PDF"
      >
        📎
      </button>

      <textarea
        v-model="inputMessage"
        @keydown.enter.exact.prevent="sendMessage"
        placeholder="Ask Rick about documents, dates, or personal info..."
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
        v-if="isLoading"
        @click="cancelStream"
        class="cancel-button"
      >
        Cancel
      </button>
      <button
        v-else
        @click="sendMessage"
        :disabled="!inputMessage.trim() && pendingFiles.length === 0"
        class="send-button"
      >
        {{ isUploading ? 'Uploading...' : 'Send' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.rick-chat {
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
  font-size: 16px;
  color: #f97316;
  width: 150px;
  touch-action: manipulation;
}

.session-name-input:hover {
  border-color: #374151;
}

.session-name-input:focus {
  outline: none;
  border-color: #f97316;
  background: #431407;
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
  background: #f97316;
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
  background: #431407;
  border: 1px solid #f97316;
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
  background: #ea580c;
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
  font-size: 16px;
  resize: none;
  touch-action: manipulation;
  -webkit-appearance: none;
}

.message-input:focus {
  outline: none;
  border-color: #f97316;
}

.message-input:disabled {
  opacity: 0.5;
}

.send-button {
  background: #ea580c;
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
  background: #c2410c;
}

.send-button:disabled {
  background: #4b5563;
  cursor: not-allowed;
}

.cancel-button {
  background: #dc2626;
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

.cancel-button:hover {
  background: #b91c1c;
}

.resume-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #422006;
  border-top: 1px solid #854d0e;
}

.resume-text {
  flex: 1;
  font-size: 13px;
  color: #fbbf24;
}

.resume-btn {
  background: #d97706;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.resume-btn:hover {
  background: #b45309;
}

.dismiss-btn {
  background: transparent;
  border: 1px solid #854d0e;
  border-radius: 6px;
  padding: 8px 12px;
  color: #fbbf24;
  font-size: 13px;
  cursor: pointer;
}

.dismiss-btn:hover {
  background: #854d0e;
}

.message-text.streaming pre {
  display: inline;
}

.streaming-cursor {
  display: inline;
  animation: blink 1s infinite;
  color: #fb923c;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.tools-used {
  font-size: 11px;
  color: #fb923c;
  background: #431407;
  padding: 2px 8px;
  border-radius: 4px;
  margin-right: 8px;
}

/* File Upload Styles */
.hidden-file-input {
  display: none;
}

.pending-files {
  padding: 12px 20px;
  background: #1f2937;
  border-top: 1px solid #374151;
}

.pending-files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #9ca3af;
}

.clear-files-btn {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
}

.clear-files-btn:hover {
  text-decoration: underline;
}

.pending-files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pending-file {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #374151;
  border-radius: 8px;
  padding: 8px 12px;
  max-width: 200px;
}

.pending-file-preview {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-thumbnail {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 4px;
}

.file-icon {
  font-size: 24px;
}

.pending-file-info {
  flex: 1;
  min-width: 0;
}

.pending-file-name {
  font-size: 12px;
  color: #e5e7eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pending-file-size {
  font-size: 10px;
  color: #6b7280;
}

.remove-file-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  flex-shrink: 0;
}

.remove-file-btn:hover {
  color: #ef4444;
}

.input-container {
  position: relative;
}

.input-container.drag-over {
  background: #1e3a5f;
  border-color: #3b82f6;
}

.drag-overlay {
  position: absolute;
  inset: 0;
  background: rgba(59, 130, 246, 0.2);
  border: 2px dashed #3b82f6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.drag-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #3b82f6;
  font-weight: 600;
}

.drag-icon {
  font-size: 32px;
}

.attach-button {
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 8px;
  padding: 12px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.attach-button:hover:not(:disabled) {
  background: #4b5563;
}

.attach-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
