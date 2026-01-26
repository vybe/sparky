<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import 'uplot/dist/uPlot.min.css'

// Import constants
import { tabs, network, hardware, serviceLinks, availableModels, imageModels, videoModels, videoPresets } from '../constants/mobileConstants.js'

// Import formatters
import { formatRelativeTime, formatAgentCost } from '../utils/formatters.js'

// Import composables
import { useTelemetry } from '../composables/useTelemetry.js'
import { useChat } from '../composables/useChat.js'
import { useAgent } from '../composables/useAgent.js'
import { useRick } from '../composables/useRick.js'
import { useImageGeneration } from '../composables/useImageGeneration.js'
import { useVideoGeneration } from '../composables/useVideoGeneration.js'
import { useManagement } from '../composables/useManagement.js'

// Navigation
const activeTab = ref('status')
const rickOnly = ref(false)  // Rick-only mode (for ?rick=1 URL)

// API base URL
const apiBaseUrl = computed(() => '/api')

// PWA and UI helpers
function refreshPage() {
  window.location.reload()
}

const isInputFocused = ref(false)
const inputContainerTop = ref(null) // null = use CSS default, number = use top positioning

function onInputFocus(event) {
  isInputFocused.value = true
  // Trigger immediate viewport check
  handleViewportResize()
  // Scroll input into view after keyboard animates
  setTimeout(() => {
    handleViewportResize()
    event?.target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, 300)
}

function onInputBlur() {
  setTimeout(() => {
    const active = document.activeElement
    if (!active || (active.tagName !== 'TEXTAREA' && active.tagName !== 'INPUT')) {
      isInputFocused.value = false
      inputContainerTop.value = null
    }
  }, 150)
}

// Handle iOS keyboard via visualViewport API
// Use TOP positioning with transform instead of BOTTOM - more reliable on iOS
function handleViewportResize() {
  if (window.visualViewport && isInputFocused.value) {
    const viewport = window.visualViewport
    // Position at the bottom of the visual viewport using TOP
    // viewport.height gives us the visible area (excluding keyboard + accessory bar)
    // viewport.offsetTop accounts for any scroll offset
    inputContainerTop.value = viewport.offsetTop + viewport.height
  }
}

// Setup visualViewport listener
function setupViewportListener() {
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', handleViewportResize)
    window.visualViewport.addEventListener('scroll', handleViewportResize)
  }
}

function cleanupViewportListener() {
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleViewportResize)
    window.visualViewport.removeEventListener('scroll', handleViewportResize)
  }
}

function getServiceUrl(port, useLocal = false) {
  const ip = useLocal ? network.local.ip : network.tailscale.ip
  return `http://${ip}:${port}`
}

// Initialize composables
const telemetry = useTelemetry()
const chat = useChat()
const agent = useAgent(apiBaseUrl.value)
const rick = useRick(apiBaseUrl.value)
const imageGen = useImageGeneration()
const videoGen = useVideoGeneration()
const management = useManagement(apiBaseUrl.value)

// Destructure composable exports for template usage
const {
  systemStats,
  ollamaLoadedModels,
  topProcesses,
  statsLoading,
  cpuChartEl,
  memChartEl,
  gpuChartEl,
  startPolling: startTelemetryPolling,
  stopPolling: stopTelemetryPolling,
  initCharts: initTelemetryCharts,
  resizeCharts: resizeTelemetryCharts,
  cleanup: cleanupTelemetry
} = telemetry

const {
  chatModels,
  selectedChatModel,
  chatMessages,
  chatInput,
  chatLoading,
  chatContainer,
  loadedModels,
  modelLoadingState,
  modelLoadProgress,
  chatModelsError,
  chatModelsLoading,
  loadChatModels,
  checkLoadedModels,
  isModelLoaded,
  loadSelectedModel,
  sendChat,
  clearChat
} = chat

const {
  agentMessages,
  agentInput,
  agentLoading,
  agentSessionId,
  agentContainer,
  agentStatus,
  agentTotalCost,
  savedSessions,
  showSessionPicker,
  agentSessionName,
  currentTool,
  lastFailedSessionId,
  checkAgentStatus,
  loadSessions,
  saveAgentSession,
  loadAgentSession,
  deleteAgentSession,
  sendAgentMessage,
  cancelAgentStream,
  resumeLastSession,
  clearAgent,
  cleanup: cleanupAgent
} = agent

const {
  rickMessages,
  rickInput,
  rickLoading,
  rickSessionId,
  rickContainer,
  rickStatus,
  rickTotalCost,
  rickSavedSessions,
  showRickSessionPicker,
  rickSessionName,
  rickCurrentTool,
  rickLastFailedSessionId,
  checkRickStatus,
  loadRickSessions,
  saveRickSession,
  loadRickSession,
  deleteRickSession,
  sendRickMessage,
  cancelRickStream,
  resumeRickLastSession,
  clearRick,
  cleanupRick
} = rick

const {
  selectedImageModel,
  imagePrompt,
  imageGenerating,
  imageProgress,
  generatedImages,
  imageError,
  currentImageModel,
  generateImage
} = imageGen

const {
  selectedVideoModel,
  selectedVideoPreset,
  videoPrompt,
  videoGenerating,
  videoProgress,
  generatedVideos,
  videoError,
  currentVideoModel,
  generateVideo
} = videoGen

const {
  managementServices,
  containers,
  trinity,
  trinityUpdating,
  trinityUpdateResult,
  managementLoading,
  actionLoading,
  managementError,
  logsModal,
  loadManagement,
  updateTrinity,
  restartTrinity,
  performAction,
  restartService,
  startService,
  stopService,
  viewLogs,
  getStatusClass
} = management

// Goose Research Agent state
const gooseMessages = ref([])
const gooseInput = ref('')
const gooseLoading = ref(false)
const gooseStatus = ref(null)
const gooseContainer = ref(null)
const gooseMode = ref('chat')
const savedResearch = ref([])
const showResearchList = ref(false)
const selectedResearch = ref(null)

const gooseModes = [
  { id: 'chat', name: 'Quick Chat' },
  { id: 'research', name: 'Deep Research' },
]

async function checkGooseStatus() {
  try {
    const res = await fetch(`${apiBaseUrl.value}/goose/status`)
    gooseStatus.value = await res.json()
  } catch (e) {
    gooseStatus.value = { available: false, error: e.message }
  }
}

async function loadResearchFiles() {
  try {
    const res = await fetch(`${apiBaseUrl.value}/goose/research`)
    const data = await res.json()
    savedResearch.value = data.files || []
  } catch (e) {
    console.error('Failed to load research:', e)
  }
}

async function viewResearchFile(file) {
  try {
    const res = await fetch(`${apiBaseUrl.value}/goose/research/${encodeURIComponent(file.name)}`)
    const data = await res.json()
    selectedResearch.value = { ...file, content: data.content }
  } catch (e) {
    console.error('Failed to load research file:', e)
  }
}

async function deleteResearchFile(file, event) {
  event.stopPropagation()
  if (!confirm(`Delete "${file.name}"?`)) return
  try {
    await fetch(`${apiBaseUrl.value}/goose/research/${encodeURIComponent(file.name)}`, { method: 'DELETE' })
    await loadResearchFiles()
    if (selectedResearch.value?.name === file.name) {
      selectedResearch.value = null
    }
  } catch (e) {
    console.error('Failed to delete:', e)
  }
}

async function sendGooseMessage() {
  if (!gooseInput.value.trim() || gooseLoading.value) return

  const userMessage = gooseInput.value.trim()
  gooseInput.value = ''

  gooseMessages.value.push({ role: 'user', content: userMessage })
  gooseMessages.value.push({ role: 'assistant', content: '', loading: true })
  scrollGooseToBottom()

  gooseLoading.value = true

  try {
    const res = await fetch(`${apiBaseUrl.value}/goose/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage, mode: gooseMode.value })
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Request failed')
    }

    const data = await res.json()
    const lastMsg = gooseMessages.value[gooseMessages.value.length - 1]
    lastMsg.loading = false
    lastMsg.content = data.result
    lastMsg.duration = data.duration_ms
    lastMsg.sources = data.sources || []
    lastMsg.saved_file = data.saved_file

    if (data.saved_file) {
      await loadResearchFiles()
    }

    scrollGooseToBottom()
  } catch (e) {
    const lastMsg = gooseMessages.value[gooseMessages.value.length - 1]
    lastMsg.loading = false
    lastMsg.content = `Error: ${e.message}`
    lastMsg.isError = true
  } finally {
    gooseLoading.value = false
  }
}

function scrollGooseToBottom() {
  setTimeout(() => {
    if (gooseContainer.value) {
      gooseContainer.value.scrollTop = gooseContainer.value.scrollHeight
    }
  }, 50)
}

function clearGoose() {
  gooseMessages.value = []
  selectedResearch.value = null
}

function formatDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function getHostname(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url.length > 25 ? url.slice(0, 25) + '...' : url
  }
}

// Lifecycle hooks
onMounted(() => {
  // Check URL for initial tab or Rick-only mode
  const params = new URLSearchParams(window.location.search)

  // Rick-only mode: ?rick=1
  if (params.get('rick') === '1') {
    rickOnly.value = true
    activeTab.value = 'rick'
  } else {
    const tab = params.get('tab')
    if (tab && tabs.some(t => t.id === tab)) {
      activeTab.value = tab
    }
  }

  // Initialize data
  if (rickOnly.value) {
    checkRickStatus()
    loadRickSessions()
  } else {
    checkAgentStatus()
  }
  loadSessions()
  loadChatModels()
  startTelemetryPolling(apiBaseUrl.value)
  window.addEventListener('resize', resizeTelemetryCharts)

  // Setup iOS keyboard handling
  setupViewportListener()
})

onUnmounted(() => {
  stopTelemetryPolling()
  cleanupTelemetry()
  cleanupAgent()
  cleanupRick()
  window.removeEventListener('resize', resizeTelemetryCharts)
  cleanupViewportListener()
})

// Watch for tab changes
watch(activeTab, (tab) => {
  if (tab === 'status') {
    // Re-initialize charts when switching back to status tab
    // nextTick ensures DOM elements are ready
    nextTick(() => initTelemetryCharts())
  }
  if (tab === 'agent' && !agentStatus.value) checkAgentStatus()
  if (tab === 'rick' && !rickStatus.value) {
    checkRickStatus()
    loadRickSessions()
  }
  if (tab === 'goose' && !gooseStatus.value) {
    checkGooseStatus()
    loadResearchFiles()
  }
  if (tab === 'chat' && chatModels.value.length === 0) loadChatModels()
  if (tab === 'manage') loadManagement()
})
</script>
<template>
  <div class="mobile-app">
    <!-- Header -->
    <header class="mobile-header" :class="{ 'rick-only-header': rickOnly }">
      <div class="header-content">
        <div class="app-title">{{ rickOnly ? 'Rick' : 'Sparky' }}</div>
        <div class="header-actions">
          <button @click="refreshPage" class="refresh-btn" title="Refresh">↻</button>
          <div class="status-dot" :class="(rickOnly ? rickStatus?.available : systemStats) ? 'online' : 'offline'"></div>
        </div>
      </div>
    </header>

    <!-- Content Area -->
    <main class="mobile-content" :class="{ 'rick-only-content': rickOnly }">
      <!-- Agent Tab (Claude Code) -->
      <div v-if="activeTab === 'agent'" class="tab-content agent-tab">
        <div class="agent-header">
          <div class="agent-status">
            <span v-if="agentStatus?.available" class="status-dot-inline online"></span>
            <span v-else class="status-dot-inline offline"></span>
            <span class="agent-version">{{ agentStatus?.available ? agentStatus.version : 'Offline' }}</span>
          </div>
          <div class="agent-controls">
            <span v-if="agentTotalCost > 0" class="agent-cost">{{ formatAgentCost(agentTotalCost) }}</span>
            <button @click="showSessionPicker = !showSessionPicker" class="btn-icon sessions-btn">
              📂<span v-if="savedSessions.length" class="session-badge">{{ savedSessions.length }}</span>
            </button>
            <button @click="clearAgent" class="btn-icon">➕</button>
          </div>
        </div>

        <!-- Session Picker -->
        <div v-if="showSessionPicker" class="session-picker-mobile">
          <div class="session-picker-header">
            <span>Saved Sessions</span>
            <button @click="showSessionPicker = false" class="close-btn">×</button>
          </div>
          <div v-if="savedSessions.length === 0" class="no-sessions">
            No saved sessions. Start chatting to create one.
          </div>
          <div v-else class="session-list-mobile">
            <div
              v-for="session in savedSessions"
              :key="session.session_id"
              @click="loadAgentSession(session)"
              class="session-item-mobile"
              :class="{ active: session.session_id === agentSessionId }"
            >
              <div class="session-item-info">
                <div class="session-name">{{ session.name }}</div>
                <div class="session-preview">{{ session.first_message || '...' }}</div>
              </div>
              <div class="session-item-actions">
                <span class="session-time">{{ formatRelativeTime(session.updated_at) }}</span>
                <button @click="deleteAgentSession(session, $event)" class="delete-btn">×</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Session Name (when active) -->
        <div v-if="agentSessionId && !showSessionPicker" class="active-session-bar">
          <input
            v-model="agentSessionName"
            @blur="saveAgentSession"
            @focus="onInputFocus($event)"
            inputmode="text"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="words"
            class="session-name-input"
            placeholder="Name this session..."
          />
          <span class="session-id-badge">{{ agentSessionId.slice(0, 6) }}</span>
        </div>

        <div ref="agentContainer" class="agent-messages">
          <div v-if="agentMessages.length === 0" class="empty-state agent-empty">
            <div class="agent-icon">🤖</div>
            <div class="agent-title">Claude Code Agent</div>
            <div class="agent-desc">Full DGX system access</div>
            <div class="agent-examples">
              <button @click="agentInput = 'What containers are running?'" class="example-chip">containers?</button>
              <button @click="agentInput = 'Show GPU usage'" class="example-chip">GPU usage</button>
              <button @click="agentInput = 'Check disk space'" class="example-chip">disk space</button>
            </div>
          </div>
          <div v-for="(msg, idx) in agentMessages" :key="idx" :class="['message', msg.role]">
            <div class="message-bubble">
              <div v-if="msg.loading && !msg.content" class="typing">
                <span></span><span></span><span></span>
                <span class="typing-label">{{ currentTool ? `Using ${currentTool}...` : 'Thinking...' }}</span>
              </div>
              <template v-else>
                <pre class="message-text" :class="{ 'error-text': msg.isError, 'streaming-text': msg.streaming }">{{ msg.content }}</pre>
                <span v-if="msg.streaming && msg.loading" class="streaming-cursor">▋</span>
              </template>
            </div>
            <div v-if="msg.role === 'assistant' && !msg.loading" class="message-meta-mobile">
              <span v-if="msg.tools && msg.tools.length" class="tools-badge">🔧 {{ msg.tools.join(', ') }}</span>
              <span v-if="msg.cost" class="message-cost">{{ formatAgentCost(msg.cost) }}</span>
              <span v-if="msg.duration" class="message-duration">{{ formatDuration(msg.duration) }}</span>
            </div>
          </div>
        </div>

        <!-- Resume Banner -->
        <div v-if="lastFailedSessionId && !agentLoading" class="resume-banner-mobile">
          <span class="resume-text-mobile">⚠️ Task may have completed</span>
          <button @click="resumeLastSession" class="resume-btn-mobile">Resume</button>
          <button @click="lastFailedSessionId = null" class="dismiss-btn-mobile">×</button>
        </div>

        <div
          class="agent-input-container"
          :class="{ 'input-focused': isInputFocused }"
          :style="inputContainerTop !== null ? { top: inputContainerTop + 'px', bottom: 'auto', transform: 'translateY(-100%)' } : {}"
        >
          <textarea
            v-model="agentInput"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            @keydown.enter.exact.prevent="sendAgentMessage"
            placeholder="Send command to Claude..."
            rows="1"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="agent-input"
          ></textarea>
          <button v-if="agentLoading" @click="cancelAgentStream" class="cancel-btn-mobile">✕</button>
          <button v-else @click="sendAgentMessage" :disabled="!agentInput.trim()" class="send-btn agent">➤</button>
        </div>
      </div>

      <!-- Rick Tab (Family Assistant) -->
      <div v-if="activeTab === 'rick'" class="tab-content rick-tab">
        <div class="rick-header">
          <div class="rick-status">
            <span v-if="rickStatus?.available" class="status-dot-inline online"></span>
            <span v-else class="status-dot-inline offline"></span>
            <span class="rick-version">{{ rickStatus?.available ? rickStatus.version : 'Offline' }}</span>
          </div>
          <div class="rick-controls">
            <span v-if="rickTotalCost > 0" class="rick-cost">{{ formatAgentCost(rickTotalCost) }}</span>
            <button @click="showRickSessionPicker = !showRickSessionPicker" class="btn-icon sessions-btn">
              📂<span v-if="rickSavedSessions.length" class="session-badge rick-badge">{{ rickSavedSessions.length }}</span>
            </button>
            <button @click="clearRick" class="btn-icon">➕</button>
          </div>
        </div>

        <!-- Rick Session Picker -->
        <div v-if="showRickSessionPicker" class="session-picker-mobile rick-session-picker">
          <div class="session-picker-header">
            <span>Saved Sessions</span>
            <button @click="showRickSessionPicker = false" class="close-btn">×</button>
          </div>
          <div v-if="rickSavedSessions.length === 0" class="no-sessions">
            No saved sessions. Start chatting to create one.
          </div>
          <div v-else class="session-list-mobile">
            <div
              v-for="session in rickSavedSessions"
              :key="session.session_id"
              @click="loadRickSession(session)"
              class="session-item-mobile"
              :class="{ active: session.session_id === rickSessionId }"
            >
              <div class="session-item-info">
                <div class="session-name">{{ session.name }}</div>
                <div class="session-preview">{{ session.first_message || '...' }}</div>
              </div>
              <div class="session-item-actions">
                <span class="session-time">{{ formatRelativeTime(session.updated_at) }}</span>
                <button @click="deleteRickSession(session, $event)" class="delete-btn">×</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Rick Session Name (when active) -->
        <div v-if="rickSessionId && !showRickSessionPicker" class="active-session-bar rick-session-bar">
          <input
            v-model="rickSessionName"
            @blur="saveRickSession"
            @focus="onInputFocus($event)"
            inputmode="text"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="words"
            class="session-name-input rick-session-input"
            placeholder="Name this session..."
          />
          <span class="session-id-badge rick-id-badge">{{ rickSessionId.slice(0, 6) }}</span>
        </div>

        <div ref="rickContainer" class="rick-messages">
          <div v-if="rickMessages.length === 0" class="empty-state rick-empty">
            <div class="rick-icon">🧑‍💼</div>
            <div class="rick-title">Rick - Family Assistant</div>
            <div class="rick-desc">Documents & personal info</div>
            <div class="rick-examples">
              <button @click="rickInput = 'What files are available?'" class="example-chip rick-chip">Available files</button>
              <button @click="rickInput = 'Search for a document'" class="example-chip rick-chip">Search docs</button>
              <button @click="rickInput = 'Help me organize'" class="example-chip rick-chip">Organize</button>
            </div>
          </div>
          <div v-for="(msg, idx) in rickMessages" :key="idx" :class="['message', msg.role]">
            <div class="message-bubble rick-bubble">
              <div v-if="msg.loading && !msg.content" class="typing">
                <span></span><span></span><span></span>
                <span class="typing-label">{{ rickCurrentTool ? `Using ${rickCurrentTool}...` : 'Thinking...' }}</span>
              </div>
              <template v-else>
                <pre class="message-text" :class="{ 'error-text': msg.isError, 'streaming-text': msg.streaming }">{{ msg.content }}</pre>
                <span v-if="msg.streaming && msg.loading" class="streaming-cursor rick-cursor">▋</span>
              </template>
            </div>
            <div v-if="msg.role === 'assistant' && !msg.loading" class="message-meta-mobile">
              <span v-if="msg.tools && msg.tools.length" class="tools-badge rick-tools">🔧 {{ msg.tools.join(', ') }}</span>
              <span v-if="msg.cost" class="message-cost">{{ formatAgentCost(msg.cost) }}</span>
              <span v-if="msg.duration" class="message-duration">{{ formatDuration(msg.duration) }}</span>
            </div>
          </div>
        </div>

        <!-- Rick Resume Banner -->
        <div v-if="rickLastFailedSessionId && !rickLoading" class="resume-banner-mobile rick-resume">
          <span class="resume-text-mobile">⚠️ Task may have completed</span>
          <button @click="resumeRickLastSession" class="resume-btn-mobile">Resume</button>
          <button @click="rickLastFailedSessionId = null" class="dismiss-btn-mobile">×</button>
        </div>

        <div
          class="rick-input-container"
          :class="{ 'input-focused': isInputFocused }"
          :style="inputContainerTop !== null ? { top: inputContainerTop + 'px', bottom: 'auto', transform: 'translateY(-100%)' } : {}"
        >
          <textarea
            v-model="rickInput"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            @keydown.enter.exact.prevent="sendRickMessage"
            placeholder="Ask Rick about documents..."
            rows="1"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="rick-input"
          ></textarea>
          <button v-if="rickLoading" @click="cancelRickStream" class="cancel-btn-mobile">✕</button>
          <button v-else @click="sendRickMessage" :disabled="!rickInput.trim()" class="send-btn rick">➤</button>
        </div>
      </div>

      <!-- Goose Tab -->
      <div v-if="activeTab === 'goose'" class="tab-content goose-tab">
        <div class="goose-header">
          <div class="goose-status">
            <span v-if="gooseStatus?.available" class="status-dot-inline online"></span>
            <span v-else class="status-dot-inline offline"></span>
            <span class="goose-version">{{ gooseStatus?.available ? gooseStatus.version : 'Offline' }}</span>
          </div>
          <div class="goose-controls">
            <select v-model="gooseMode" class="mode-select-mini">
              <option v-for="m in gooseModes" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
            <button @click="showResearchList = !showResearchList" class="btn-icon research-btn">
              📚<span v-if="savedResearch.length" class="research-badge">{{ savedResearch.length }}</span>
            </button>
            <button @click="clearGoose" class="btn-icon">➕</button>
          </div>
        </div>

        <!-- Research Files List -->
        <div v-if="showResearchList" class="research-list-mobile">
          <div class="research-list-header">
            <span>Saved Research</span>
            <button @click="showResearchList = false" class="close-btn">×</button>
          </div>
          <div v-if="savedResearch.length === 0" class="no-research">
            No saved research yet. Use Deep Research mode.
          </div>
          <div v-else class="research-items">
            <div
              v-for="file in savedResearch"
              :key="file.name"
              @click="viewResearchFile(file)"
              class="research-file-item"
              :class="{ active: selectedResearch?.name === file.name }"
            >
              <div class="research-file-info">
                <div class="research-file-name">{{ file.name.replace('.md', '') }}</div>
                <div class="research-file-meta">{{ formatRelativeTime(file.modified) }}</div>
              </div>
              <button @click="deleteResearchFile(file, $event)" class="delete-btn">×</button>
            </div>
          </div>
          <!-- Research Preview -->
          <div v-if="selectedResearch" class="research-preview-mobile">
            <div class="research-preview-header">{{ selectedResearch.name }}</div>
            <pre class="research-preview-content">{{ selectedResearch.content }}</pre>
          </div>
        </div>

        <div ref="gooseContainer" class="goose-messages">
          <div v-if="gooseMessages.length === 0" class="empty-state goose-empty">
            <div class="goose-icon">🪿</div>
            <div class="goose-title">Goose Research Agent</div>
            <div class="goose-desc">Web search + research notes</div>
            <div class="goose-examples">
              <button @click="gooseInput = 'Latest AI agent frameworks'" class="example-chip">AI frameworks</button>
              <button @click="gooseInput = 'Compare local LLM options'" class="example-chip">LLM comparison</button>
              <button @click="gooseInput = 'MCP protocol overview'" class="example-chip">MCP protocol</button>
            </div>
          </div>
          <div v-for="(msg, idx) in gooseMessages" :key="idx" :class="['message', msg.role]">
            <div class="message-bubble goose-bubble">
              <div v-if="msg.loading" class="typing"><span></span><span></span><span></span></div>
              <pre v-else class="message-text" :class="{ 'error-text': msg.isError }">{{ msg.content }}</pre>
              <!-- Sources -->
              <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
                <div class="sources-label">Sources:</div>
                <div class="sources-list">
                  <a v-for="(src, sidx) in msg.sources" :key="sidx" :href="src" target="_blank" class="source-chip">
                    {{ getHostname(src) }}
                  </a>
                </div>
              </div>
              <!-- Saved indicator -->
              <div v-if="msg.saved_file" class="saved-indicator">💾 {{ msg.saved_file }}</div>
            </div>
            <div v-if="msg.role === 'assistant' && !msg.loading && msg.duration" class="message-duration">
              {{ formatDuration(msg.duration) }}
            </div>
          </div>
        </div>

        <div
          class="goose-input-container"
          :class="{ 'input-focused': isInputFocused }"
          :style="inputContainerTop !== null ? { top: inputContainerTop + 'px', bottom: 'auto', transform: 'translateY(-100%)' } : {}"
        >
          <textarea
            v-model="gooseInput"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            @keydown.enter.exact.prevent="sendGooseMessage"
            :placeholder="gooseMode === 'research' ? 'Research topic...' : 'Ask anything...'"
            rows="1"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="goose-input"
          ></textarea>
          <button @click="sendGooseMessage" :disabled="gooseLoading || !gooseInput.trim()" class="send-btn goose">
            <span v-if="gooseLoading">...</span>
            <span v-else>➤</span>
          </button>
        </div>
      </div>

      <!-- Chat Tab -->
      <div v-if="activeTab === 'chat'" class="tab-content chat-tab">
        <!-- Error loading models -->
        <div v-if="chatModelsError" class="model-error">
          <div class="error-message">{{ chatModelsError }}</div>
          <button @click="loadChatModels" class="retry-btn">🔄 Retry</button>
        </div>

        <!-- Loading models -->
        <div v-if="chatModelsLoading" class="model-loading">
          Loading models...
        </div>

        <div class="model-selector">
          <select v-model="selectedChatModel" class="model-select" :disabled="chatModels.length === 0">
            <option v-if="chatModels.length === 0" value="">No models available</option>
            <option v-for="m in chatModels" :key="m.name" :value="m.name">
              {{ m.name.split(':')[0] }} {{ isModelLoaded(m.name) ? '✓' : '' }}
            </option>
          </select>
          <button
            v-if="!isModelLoaded(selectedChatModel) && selectedChatModel"
            @click="loadSelectedModel"
            :disabled="modelLoadingState === 'loading'"
            class="btn-load"
          >
            {{ modelLoadingState === 'loading' ? '⏳' : '📥' }}
          </button>
          <span v-else-if="selectedChatModel" class="model-loaded">✓</span>
          <button @click="clearChat" class="btn-icon">🗑️</button>
        </div>

        <!-- Model load progress -->
        <div v-if="modelLoadProgress" class="model-progress">
          {{ modelLoadProgress }}
        </div>

        <!-- Warning if model not loaded -->
        <div v-if="!isModelLoaded(selectedChatModel) && modelLoadingState !== 'loading' && selectedChatModel" class="model-warning">
          ⚠️ Model not loaded. Tap 📥 to load first (large models take 30-90s).
        </div>

        <div ref="chatContainer" class="chat-messages">
          <div v-if="chatMessages.length === 0" class="empty-state">Start chatting with AI</div>
          <div v-for="(msg, idx) in chatMessages" :key="idx" :class="['message', msg.role]">
            <div class="message-bubble">
              <div v-if="msg.loading" class="typing"><span></span><span></span><span></span></div>
              <div v-else class="message-text">{{ msg.content }}</div>
            </div>
          </div>
        </div>

        <div
          class="chat-input-container"
          :class="{ 'input-focused': isInputFocused }"
          :style="inputContainerTop !== null ? { top: inputContainerTop + 'px', bottom: 'auto', transform: 'translateY(-100%)' } : {}"
        >
          <textarea
            v-model="chatInput"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            @keydown.enter.exact.prevent="sendChat"
            :placeholder="selectedChatModel ? 'Type a message...' : 'Select a model first...'"
            :disabled="!selectedChatModel"
            rows="1"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="chat-input"
          ></textarea>
          <button @click="sendChat" :disabled="chatLoading || !chatInput.trim() || !selectedChatModel" class="send-btn">
            <span v-if="chatLoading">...</span>
            <span v-else>➤</span>
          </button>
        </div>
      </div>

      <!-- Image Tab -->
      <div v-if="activeTab === 'image'" class="tab-content image-tab">
        <div class="gen-controls">
          <select v-model="selectedImageModel" class="model-select">
            <option v-for="m in imageModels" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
          <textarea
            v-model="imagePrompt"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            placeholder="Describe your image..."
            rows="3"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="prompt-input"
          ></textarea>
          <button @click="generateImage" :disabled="imageGenerating" class="generate-btn">
            <span v-if="imageGenerating">Generating... {{ imageProgress }}%</span>
            <span v-else>Generate Image</span>
          </button>
          <div v-if="imageGenerating" class="progress-bar"><div class="progress-fill" :style="{ width: `${imageProgress}%` }"></div></div>
          <div v-if="imageError" class="error">{{ imageError }}</div>
        </div>
        <div class="generated-gallery">
          <div v-for="(img, idx) in generatedImages" :key="idx" class="gallery-item">
            <img :src="img.url" :alt="img.prompt" />
            <div class="gallery-info">{{ img.model }}</div>
          </div>
          <div v-if="generatedImages.length === 0" class="empty-state">No images yet</div>
        </div>
      </div>

      <!-- Video Tab -->
      <div v-if="activeTab === 'video'" class="tab-content video-tab">
        <div class="gen-controls">
          <select v-model="selectedVideoModel" class="model-select">
            <option v-for="m in videoModels" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
          <select v-model="selectedVideoPreset" class="model-select">
            <option v-for="p in videoPresets" :key="p.name" :value="p">{{ p.name }}</option>
          </select>
          <textarea
            v-model="videoPrompt"
            @focus="onInputFocus($event)"
            @blur="onInputBlur"
            placeholder="Describe your video scene..."
            rows="3"
            inputmode="text"
            autocomplete="off"
            autocorrect="on"
            autocapitalize="sentences"
            class="prompt-input"
          ></textarea>
          <button @click="generateVideo" :disabled="videoGenerating" class="generate-btn video">
            <span v-if="videoGenerating">Generating... {{ Math.round(videoProgress) }}%</span>
            <span v-else>Generate Video</span>
          </button>
          <div v-if="videoGenerating" class="progress-bar video"><div class="progress-fill" :style="{ width: `${videoProgress}%` }"></div></div>
          <div v-if="videoError" class="error">{{ videoError }}</div>
        </div>
        <div class="generated-gallery">
          <div v-for="(vid, idx) in generatedVideos" :key="idx" class="gallery-item video">
            <video :src="vid.url" controls loop playsinline></video>
            <div class="gallery-info">{{ vid.model }} - {{ vid.preset }}</div>
          </div>
          <div v-if="generatedVideos.length === 0" class="empty-state">No videos yet</div>
        </div>
      </div>

      <!-- Status Tab -->
      <div v-if="activeTab === 'status'" class="tab-content status-tab">
        <!-- Live Stats with Charts -->
        <div class="section-title">Live Stats</div>
        <div v-if="statsLoading" class="loading">Loading...</div>
        <div v-else class="stats-grid">
          <div class="stat-card-chart">
            <div class="stat-header">
              <div class="stat-icon">💻</div>
              <div class="stat-label">CPU</div>
              <div class="stat-value-chart">{{ systemStats?.cpu?.percent?.toFixed(0) || '0' }}%</div>
            </div>
            <div ref="cpuChartEl" class="chart-container"></div>
          </div>

          <div class="stat-card-chart">
            <div class="stat-header">
              <div class="stat-icon">🧠</div>
              <div class="stat-label">Memory</div>
              <div class="stat-value-chart">{{ systemStats?.memory?.percent?.toFixed(0) || '0' }}%</div>
            </div>
            <div ref="memChartEl" class="chart-container"></div>
          </div>

          <div class="stat-card-chart">
            <div class="stat-header">
              <div class="stat-icon">🔥</div>
              <div class="stat-label">GPU Temp</div>
              <div class="stat-value-chart">{{ systemStats?.gpu?.temp || '-' }}°C</div>
            </div>
            <div ref="gpuChartEl" class="chart-container"></div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">💾</div>
            <div class="stat-info">
              <div class="stat-label">Disk</div>
              <div class="stat-value" v-if="systemStats?.disk">{{ systemStats.disk.percent?.toFixed(0) }}%</div>
              <div v-else class="stat-value">N/A</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">⚡</div>
            <div class="stat-info">
              <div class="stat-label">GPU Power</div>
              <div class="stat-value" v-if="systemStats?.gpu">{{ systemStats.gpu.power }}W</div>
              <div v-else class="stat-value">N/A</div>
            </div>
          </div>
        </div>

        <!-- Top Processes -->
        <div class="section-title">Top Processes</div>
        <div class="processes-grid">
          <!-- GPU Processes -->
          <div class="process-card">
            <div class="process-header gpu">🎮 GPU Memory</div>
            <div v-if="topProcesses.gpu_processes?.length" class="process-list">
              <div v-for="p in topProcesses.gpu_processes" :key="p.pid" class="process-row">
                <span class="process-name">{{ p.name }}</span>
                <span class="process-value gpu">{{ (p.gpu_memory_mb / 1024).toFixed(1) }}GB</span>
              </div>
            </div>
            <div v-else class="process-empty">No GPU processes</div>
          </div>

          <!-- Memory Processes -->
          <div class="process-card">
            <div class="process-header mem">🧠 Memory</div>
            <div class="process-list">
              <div v-for="p in topProcesses.top_memory?.slice(0, 3)" :key="p.pid" class="process-item">
                <div class="process-row">
                  <span class="process-name">{{ p.name }}</span>
                  <span class="process-value mem">{{ (p.memory_mb / 1024).toFixed(1) }}GB</span>
                </div>
                <div class="process-cmd">{{ p.cmdline }}</div>
              </div>
            </div>
          </div>

          <!-- CPU Processes -->
          <div class="process-card">
            <div class="process-header cpu">💻 CPU</div>
            <div class="process-list">
              <div v-for="p in topProcesses.top_cpu?.slice(0, 3)" :key="p.pid" class="process-item">
                <div class="process-row">
                  <span class="process-name">{{ p.name }}</span>
                  <span class="process-value cpu">{{ p.cpu_percent }}%</span>
                </div>
                <div class="process-cmd">{{ p.cmdline }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Hardware Info -->
        <div class="section-title">Hardware</div>
        <div class="info-card">
          <div class="info-row"><span class="info-label">GPU</span><span class="info-value">{{ hardware.gpu.name }} ({{ hardware.gpu.arch }})</span></div>
          <div class="info-row"><span class="info-label">CPU</span><span class="info-value">{{ hardware.cpu.name }}</span></div>
          <div class="info-row"><span class="info-label">Memory</span><span class="info-value">{{ hardware.memory.size }} {{ hardware.memory.type }}</span></div>
          <div class="info-row"><span class="info-label">Storage</span><span class="info-value">{{ hardware.storage.size }} ({{ hardware.storage.free }} free)</span></div>
        </div>

        <!-- Network -->
        <div class="section-title">Network</div>
        <div class="info-card">
          <div class="info-row"><span class="info-label">🏠 Local</span><span class="info-value mono">{{ network.local.ip }}</span></div>
          <div class="info-row"><span class="info-label">🌐 Tailscale</span><span class="info-value mono">{{ network.tailscale.ip }}</span></div>
        </div>

        <!-- Service Links -->
        <div class="section-title">Quick Links</div>
        <div class="service-links">
          <a v-for="s in serviceLinks" :key="s.name" :href="getServiceUrl(s.port)" target="_blank" class="service-link">
            <span class="service-icon">{{ s.icon }}</span>
            <span class="service-name">{{ s.name }}</span>
          </a>
        </div>

        <!-- Available Models -->
        <div class="section-title">Available Models</div>
        <div class="models-grid">
          <div class="model-category">
            <div class="category-title">💬 LLMs</div>
            <div class="model-tags">
              <span v-for="m in availableModels.llm" :key="m" class="model-tag">{{ m.split(':')[0] }}</span>
            </div>
          </div>
          <div class="model-category">
            <div class="category-title">🎬 Video</div>
            <div class="model-tags">
              <span v-for="m in availableModels.video" :key="m" class="model-tag">{{ m }}</span>
            </div>
          </div>
          <div class="model-category">
            <div class="category-title">🎨 Image</div>
            <div class="model-tags">
              <span v-for="m in availableModels.image" :key="m" class="model-tag">{{ m }}</span>
            </div>
          </div>
          <div class="model-category">
            <div class="category-title">🎤 Audio</div>
            <div class="model-tags">
              <span v-for="m in availableModels.audio" :key="m" class="model-tag">{{ m }}</span>
            </div>
          </div>
        </div>

        <!-- Loaded Models -->
        <div v-if="ollamaLoadedModels.length" class="section-title">Loaded in Memory</div>
        <div v-if="ollamaLoadedModels.length" class="loaded-models">
          <div v-for="m in ollamaLoadedModels" :key="m.name" class="loaded-model">
            <span class="loaded-name">{{ m.name.split(':')[0] }}</span>
            <span class="loaded-size">{{ (m.size / 1e9).toFixed(1) }}GB</span>
          </div>
        </div>

        <button @click="loadStats" class="refresh-btn">↻ Refresh Stats</button>
      </div>

      <!-- Manage Tab -->
      <div v-if="activeTab === 'manage'" class="tab-content manage-tab">
        <div v-if="managementError" class="error-banner">
          {{ managementError }}
          <button @click="managementError = ''" class="error-close">×</button>
        </div>

        <div v-if="managementLoading" class="loading">Loading services...</div>

        <template v-else>
          <!-- Trinity Section -->
          <div class="trinity-section">
            <div class="trinity-header">
              <img src="/trinity-logo.svg" alt="Trinity" class="trinity-logo" />
              <div class="trinity-info">
                <div class="trinity-title">Trinity</div>
                <div v-if="trinity.version" class="trinity-version">{{ trinity.version }}</div>
              </div>
            </div>

            <div class="trinity-actions">
              <button
                @click="updateTrinity"
                :disabled="trinityUpdating"
                class="trinity-update-btn"
              >
                <span v-if="trinityUpdating" class="spinning">↻</span>
                <span v-else>⬆</span>
                {{ trinityUpdating ? 'Updating...' : 'Update' }}
              </button>
              <button
                @click="restartTrinity"
                :disabled="actionLoading['trinity-restart']"
                class="trinity-restart-btn"
              >
                {{ actionLoading['trinity-restart'] ? '...' : '↻ Restart' }}
              </button>
            </div>

            <!-- Update Result -->
            <div v-if="trinityUpdateResult" :class="['trinity-result', trinityUpdateResult.success ? 'success' : 'error']">
              {{ trinityUpdateResult.success ? '✓ Updated' : '✗ ' + trinityUpdateResult.error }}
            </div>

            <!-- Trinity Services -->
            <div class="trinity-services">
              <div v-for="s in trinity.services" :key="s.name" class="trinity-service">
                <span class="trinity-service-name">{{ s.name }}</span>
                <span :class="['status-badge', getStatusClass(s.status)]">{{ s.status }}</span>
              </div>
            </div>
          </div>

          <!-- Managed Services -->
          <div class="section-title">Services</div>
          <div class="services-list">
            <div v-for="service in managementServices" :key="service.name" class="service-card">
              <div class="service-header">
                <span class="service-title">{{ service.name }}</span>
                <span :class="['status-badge', getStatusClass(service.status)]">{{ service.status }}</span>
              </div>
              <div class="service-desc">{{ service.description }}</div>
              <div class="service-actions">
                <!-- Start button (if stopped) -->
                <button
                  v-if="service.status === 'stopped' && service.name === 'ollama'"
                  @click="startService(service.name)"
                  :disabled="actionLoading[`service-${service.name}-start`]"
                  class="action-btn start"
                >
                  {{ actionLoading[`service-${service.name}-start`] ? '...' : '▶ Start' }}
                </button>
                <!-- Stop button (if running) -->
                <button
                  v-if="service.status === 'running' && service.name === 'ollama'"
                  @click="stopService(service.name)"
                  :disabled="actionLoading[`service-${service.name}-stop`]"
                  class="action-btn stop"
                >
                  {{ actionLoading[`service-${service.name}-stop`] ? '...' : '⬛ Stop' }}
                </button>
                <!-- Restart button -->
                <button
                  @click="restartService(service.name)"
                  :disabled="actionLoading[`service-${service.name}-restart`] || service.status === 'not found'"
                  class="action-btn restart"
                >
                  {{ actionLoading[`service-${service.name}-restart`] ? '...' : '↻' }}
                </button>
                <!-- Logs button (only for containers) -->
                <button
                  v-if="service.container"
                  @click="viewLogs(service.container)"
                  :disabled="service.status === 'not found'"
                  class="action-btn logs"
                >
                  Logs
                </button>
              </div>
            </div>
          </div>

          <!-- Containers -->
          <div class="section-title">Containers</div>
          <div class="containers-list">
            <div v-for="container in containers" :key="container.id" class="container-card">
              <div class="container-header">
                <span class="container-name">{{ container.name }}</span>
                <span :class="['status-badge', getStatusClass(container.status)]">{{ container.status }}</span>
              </div>
              <div class="container-image">{{ container.image?.split('/').pop()?.split(':')[0] || container.image }}</div>
              <div class="container-actions">
                <button
                  v-if="container.status !== 'running'"
                  @click="performAction(container.name, 'start')"
                  :disabled="actionLoading[`${container.name}-start`]"
                  class="action-btn start"
                >
                  {{ actionLoading[`${container.name}-start`] ? '...' : '▶ Start' }}
                </button>
                <button
                  v-if="container.status === 'running'"
                  @click="performAction(container.name, 'stop')"
                  :disabled="actionLoading[`${container.name}-stop`]"
                  class="action-btn stop"
                >
                  {{ actionLoading[`${container.name}-stop`] ? '...' : '⬛ Stop' }}
                </button>
                <button
                  @click="performAction(container.name, 'restart')"
                  :disabled="actionLoading[`${container.name}-restart`]"
                  class="action-btn restart"
                >
                  {{ actionLoading[`${container.name}-restart`] ? '...' : '↻' }}
                </button>
                <button @click="viewLogs(container.name)" class="action-btn logs">Logs</button>
              </div>
            </div>
          </div>

          <button @click="loadManagement" class="refresh-btn">↻ Refresh</button>
        </template>
      </div>
    </main>

    <!-- Bottom Navigation (hidden in Rick-only mode) -->
    <nav v-if="!rickOnly" class="mobile-nav" :class="{ 'nav-hidden': isInputFocused }">
      <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id" :class="['nav-btn', { active: activeTab === tab.id }]">
        <span class="nav-icon">{{ tab.icon }}</span>
        <span class="nav-label">{{ tab.name }}</span>
      </button>
    </nav>

    <!-- Logs Modal -->
    <div v-if="logsModal.visible" class="logs-modal" @click.self="logsModal.visible = false">
      <div class="logs-content">
        <div class="logs-header">
          <span>{{ logsModal.container }}</span>
          <button @click="logsModal.visible = false" class="logs-close">×</button>
        </div>
        <pre class="logs-text">{{ logsModal.content }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mobile-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: #111827;
  color: white;
  overflow: hidden;
}

/* Header */
.mobile-header {
  flex-shrink: 0;
  background: #1f2937;
  padding: calc(var(--sat, 0px) + 6px) 12px 6px;
  border-bottom: 1px solid #374151;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-title {
  font-size: 15px;
  font-weight: 600;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online { background: #22c55e; }
.status-dot.offline { background: #ef4444; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  background: transparent;
  border: none;
  color: #6b7280;
  font-size: 14px;
  padding: 2px 4px;
  cursor: pointer;
  line-height: 1;
}

.refresh-btn:active {
  color: white;
}

/* Content */
.mobile-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.tab-content {
  min-height: 100%;
  padding: 16px;
  padding-bottom: calc(80px + var(--sab, 0px));
}

/* Section Titles */
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  margin: 16px 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-title:first-child {
  margin-top: 0;
}

/* Agent Tab */
.agent-tab {
  display: flex;
  flex-direction: column;
  padding-bottom: calc(140px + var(--sab, 0px));
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.agent-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot-inline {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot-inline.online { background: #22c55e; }
.status-dot-inline.offline { background: #ef4444; }

.agent-version {
  font-size: 12px;
  color: #9ca3af;
}

.agent-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-cost {
  font-size: 11px;
  color: #9ca3af;
  background: #374151;
  padding: 4px 8px;
  border-radius: 6px;
}

.sessions-btn {
  position: relative;
}

.session-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #3b82f6;
  color: white;
  font-size: 10px;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-picker-mobile {
  background: #1f2937;
  border-radius: 12px;
  margin: 8px 0;
  max-height: 250px;
  overflow-y: auto;
}

.session-picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #374151;
  font-weight: 600;
  color: #9ca3af;
}

.close-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
}

.no-sessions {
  padding: 24px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}

.session-list-mobile {
  padding: 8px;
}

.session-item-mobile {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}

.session-item-mobile:hover,
.session-item-mobile:active {
  background: #374151;
}

.session-item-mobile.active {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
}

.session-item-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-size: 14px;
  font-weight: 500;
  color: #e5e7eb;
  margin-bottom: 2px;
}

.session-preview {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 8px;
}

.session-time {
  font-size: 11px;
  color: #6b7280;
}

.delete-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
}

.delete-btn:active {
  color: #ef4444;
}

.active-session-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #1e3a5f;
  border-radius: 8px;
  margin: 8px 0;
}

.session-name-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #93c5fd;
  font-size: 16px; /* Minimum 16px prevents iOS zoom */
  padding: 4px;
  touch-action: manipulation;
}

.session-name-input:focus {
  outline: none;
}

.session-id-badge {
  font-size: 10px;
  color: #6b7280;
  font-family: monospace;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 60px;
}

.agent-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.agent-title {
  font-size: 18px;
  font-weight: 600;
  color: #d1d5db;
  margin-bottom: 4px;
}

.agent-desc {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 16px;
}

.agent-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.example-chip {
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 16px;
  padding: 6px 14px;
  font-size: 12px;
  color: #d1d5db;
  cursor: pointer;
}

.example-chip:active {
  background: #4b5563;
}

.message-cost {
  font-size: 10px;
  color: #6b7280;
  margin-top: 4px;
  margin-left: 16px;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 15px;
  line-height: 1.4;
}

.error-text {
  color: #f87171;
}

.agent-input-container {
  position: fixed;
  bottom: calc(70px + var(--sab, 0px));
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #1f2937;
  border-top: 1px solid #374151;
  display: flex;
  gap: 8px;
  transition: transform 0.15s ease-out, top 0.15s ease-out, bottom 0.15s ease-out;
  z-index: 100;
}

.agent-input-container.input-focused {
  /* Fallback when visualViewport style not yet applied */
  bottom: var(--sab, 0px);
}

.agent-input {
  flex: 1;
  background: #374151;
  border: none;
  border-radius: 20px;
  padding: 12px 16px;
  color: white;
  font-size: 16px;
  resize: none;
  max-height: 100px;
}

.send-btn.agent {
  background: #8b5cf6;
}

.send-btn.agent:disabled {
  background: #4b5563;
}

/* Rick Tab (Family Assistant) */
.rick-tab {
  display: flex;
  flex-direction: column;
  padding-bottom: calc(140px + var(--sab, 0px));
}

.rick-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.rick-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rick-version {
  font-size: 12px;
  color: #9ca3af;
}

.rick-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rick-cost {
  font-size: 11px;
  color: #fb923c;
  background: #431407;
  padding: 4px 8px;
  border-radius: 6px;
}

.rick-badge {
  background: #f97316;
}

.rick-session-picker {
  background: #1f2937;
}

.rick-session-bar {
  background: #431407;
  border: 1px solid #7c2d12;
}

.rick-session-input {
  color: #fb923c;
}

.rick-session-input:focus {
  background: #431407;
  border-color: #f97316;
}

.rick-id-badge {
  background: #7c2d12;
  color: #fb923c;
}

.rick-messages {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-bottom: 20px;
}

.rick-empty {
  text-align: center;
  padding: 40px 20px;
}

.rick-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.rick-title {
  font-size: 18px;
  font-weight: 600;
  color: #fb923c;
  margin-bottom: 4px;
}

.rick-desc {
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 20px;
}

.rick-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.rick-chip {
  background: #431407;
  border-color: #7c2d12;
  color: #fb923c;
}

.rick-chip:active {
  background: #7c2d12;
}

.rick-bubble {
  background: #374151;
}

.message.user .rick-bubble {
  background: #ea580c;
}

.rick-cursor {
  color: #fb923c;
}

.rick-tools {
  background: #431407;
  color: #fb923c;
}

.rick-resume {
  background: #431407;
  border-color: #7c2d12;
}

.rick-input-container {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: #111827;
  border-top: 1px solid #374151;
  position: fixed;
  bottom: calc(60px + var(--sab, 0px));
  left: 0;
  right: 0;
  z-index: 10;
}

.rick-input-container.input-focused {
  position: fixed;
  z-index: 100;
}

.rick-input {
  flex: 1;
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 20px;
  padding: 12px 16px;
  color: white;
  font-size: 16px;
  resize: none;
  min-height: 44px;
  max-height: 100px;
  touch-action: manipulation;
  -webkit-appearance: none;
}

.rick-input:focus {
  outline: none;
  border-color: #f97316;
}

.send-btn.rick {
  background: #ea580c;
}

.send-btn.rick:active {
  background: #c2410c;
}

.send-btn.rick:disabled {
  background: #4b5563;
}

/* Goose Tab */
.goose-tab {
  display: flex;
  flex-direction: column;
  padding-bottom: calc(140px + var(--sab, 0px));
}

.goose-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.goose-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.goose-version {
  font-size: 12px;
  color: #9ca3af;
}

.goose-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-select-mini {
  background: #374151;
  border: none;
  border-radius: 6px;
  padding: 8px 10px;
  color: white;
  font-size: 12px;
  -webkit-appearance: none;
}

.research-btn {
  position: relative;
}

.research-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #10b981;
  color: white;
  font-size: 10px;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.research-list-mobile {
  background: #1f2937;
  border-radius: 12px;
  margin: 8px 0;
  max-height: 300px;
  overflow-y: auto;
}

.research-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #374151;
  font-weight: 600;
  color: #9ca3af;
  font-size: 14px;
}

.no-research {
  padding: 24px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

.research-items {
  padding: 8px;
}

.research-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}

.research-file-item:active,
.research-file-item.active {
  background: #374151;
}

.research-file-info {
  flex: 1;
  min-width: 0;
}

.research-file-name {
  font-size: 13px;
  color: #e5e7eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.research-file-meta {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.research-preview-mobile {
  border-top: 1px solid #374151;
  padding: 12px;
  max-height: 150px;
  overflow-y: auto;
}

.research-preview-header {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
}

.research-preview-content {
  font-size: 11px;
  color: #d1d5db;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
  line-height: 1.4;
}

.goose-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.goose-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 60px;
}

.goose-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.goose-title {
  font-size: 18px;
  font-weight: 600;
  color: #d1d5db;
  margin-bottom: 4px;
}

.goose-desc {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 16px;
}

.goose-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.goose-bubble {
  background: #374151 !important;
}

.message.user .goose-bubble {
  background: #059669 !important;
}

.message-sources {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #4b5563;
}

.sources-label {
  font-size: 10px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-chip {
  font-size: 10px;
  color: #60a5fa;
  background: #1e3a5f;
  padding: 3px 8px;
  border-radius: 4px;
  text-decoration: none;
}

.saved-indicator {
  margin-top: 8px;
  font-size: 11px;
  color: #10b981;
}

.message-duration {
  font-size: 10px;
  color: #6b7280;
  margin-top: 4px;
  margin-left: 16px;
}

.goose-input-container {
  position: fixed;
  bottom: calc(70px + var(--sab, 0px));
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #1f2937;
  border-top: 1px solid #374151;
  display: flex;
  gap: 8px;
  transition: transform 0.15s ease-out, top 0.15s ease-out, bottom 0.15s ease-out;
  z-index: 100;
}

.goose-input-container.input-focused {
  bottom: var(--sab, 0px);
}

.goose-input {
  flex: 1;
  background: #374151;
  border: none;
  border-radius: 20px;
  padding: 12px 16px;
  color: white;
  font-size: 16px;
  resize: none;
  max-height: 100px;
}

.send-btn.goose {
  background: #059669;
}

.send-btn.goose:disabled {
  background: #4b5563;
}

/* Chat Tab */
.chat-tab {
  display: flex;
  flex-direction: column;
  padding-bottom: calc(140px + var(--sab, 0px));
}

.model-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.model-select {
  flex: 1;
  background: #374151;
  border: none;
  border-radius: 8px;
  padding: 12px;
  color: white;
  font-size: 14px;
  -webkit-appearance: none;
}

.btn-icon {
  background: #374151;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 16px;
  cursor: pointer;
}

.btn-load {
  background: #2563eb;
  border: none;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 16px;
  cursor: pointer;
  color: white;
}

.btn-load:disabled {
  background: #1e40af;
  opacity: 0.7;
}

.model-loaded {
  color: #22c55e;
  font-size: 20px;
  padding: 8px;
}

.model-progress {
  background: #1e3a5f;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #60a5fa;
  text-align: center;
}

.model-warning {
  background: #78350f;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #fbbf24;
  text-align: center;
}

.model-error {
  background: #7f1d1d;
  border: 1px solid #ef4444;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.error-message {
  flex: 1;
  font-size: 13px;
  color: #fca5a5;
}

.retry-btn {
  background: #ef4444;
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.retry-btn:active {
  background: #dc2626;
}

.model-loading {
  background: #1e3a5f;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #60a5fa;
  text-align: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 15px;
  line-height: 1.4;
}

.message.user .message-bubble {
  background: #3b82f6;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: #374151;
  border-bottom-left-radius: 4px;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.typing {
  display: flex;
  gap: 4px;
}

.typing span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1s infinite;
}

.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; }
  30% { opacity: 1; }
}

.chat-input-container {
  position: fixed;
  bottom: calc(70px + var(--sab, 0px));
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #1f2937;
  border-top: 1px solid #374151;
  display: flex;
  gap: 8px;
  transition: transform 0.15s ease-out, top 0.15s ease-out, bottom 0.15s ease-out;
  z-index: 100;
}

.chat-input-container.input-focused {
  /* Fallback when visualViewport style not yet applied */
  bottom: var(--sab, 0px);
}

.chat-input {
  flex: 1;
  background: #374151;
  border: none;
  border-radius: 20px;
  padding: 12px 16px;
  color: white;
  font-size: 16px;
  resize: none;
  max-height: 100px;
}

.chat-input:disabled {
  background: #1f2937;
  color: #6b7280;
  cursor: not-allowed;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: #3b82f6;
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 18px;
  cursor: pointer;
  flex-shrink: 0;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.send-btn:disabled {
  background: #4b5563;
}

/* Generation Tabs */
.gen-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.prompt-input {
  background: #374151;
  border: none;
  border-radius: 12px;
  padding: 14px;
  color: white;
  font-size: 16px;
  resize: none;
}

.generate-btn {
  background: #3b82f6;
  border: none;
  border-radius: 12px;
  padding: 16px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.generate-btn.video {
  background: #8b5cf6;
}

.generate-btn:disabled {
  background: #4b5563;
}

.progress-bar {
  height: 6px;
  background: #374151;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s;
}

.progress-bar.video .progress-fill {
  background: #8b5cf6;
}

.error {
  color: #f87171;
  font-size: 14px;
}

/* Gallery */
.generated-gallery {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gallery-item {
  background: #1f2937;
  border-radius: 12px;
  overflow: hidden;
}

.gallery-item img,
.gallery-item video {
  width: 100%;
  display: block;
}

.gallery-info {
  padding: 10px 12px;
  font-size: 13px;
  color: #9ca3af;
}

/* Status Tab */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-card {
  background: #1f2937;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-card-chart {
  background: #1f2937;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-icon {
  font-size: 24px;
}

.stat-label {
  font-size: 11px;
  color: #9ca3af;
  flex: 1;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
}

.stat-value-chart {
  font-size: 18px;
  font-weight: 700;
  font-family: ui-monospace, monospace;
  color: #60a5fa;
}

.chart-container {
  width: 100%;
  height: 60px;
  background: rgba(31, 41, 55, 0.5);
  border-radius: 8px;
  overflow: hidden;
}

.stat-sub {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 400;
}

/* Process Cards */
.processes-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.process-card {
  background: #1f2937;
  border-radius: 12px;
  padding: 12px;
}

.process-header {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #374151;
}

.process-header.gpu { color: #4ade80; }
.process-header.mem { color: #60a5fa; }
.process-header.cpu { color: #facc15; }

.process-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.process-item {
  padding-bottom: 8px;
  border-bottom: 1px solid #374151;
}

.process-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.process-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.process-cmd {
  font-size: 10px;
  color: #6b7280;
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
}

.process-name {
  color: #d1d5db;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60%;
}

.process-value {
  font-family: monospace;
  font-weight: 500;
}

.process-value.gpu { color: #4ade80; }
.process-value.mem { color: #60a5fa; }
.process-value.cpu { color: #facc15; }

.process-empty {
  font-size: 12px;
  color: #6b7280;
  font-style: italic;
}

/* Info Cards */
.info-card {
  background: #1f2937;
  border-radius: 12px;
  padding: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #374151;
  font-size: 13px;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: #9ca3af;
}

.info-value {
  color: white;
  text-align: right;
}

.info-value.mono {
  font-family: monospace;
}

/* Service Links */
.service-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.service-link {
  background: #1f2937;
  border-radius: 10px;
  padding: 12px 8px;
  text-align: center;
  text-decoration: none;
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.service-icon {
  font-size: 20px;
}

.service-name {
  font-size: 11px;
  color: #9ca3af;
}

/* Models Grid */
.models-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-category {
  background: #1f2937;
  border-radius: 10px;
  padding: 12px;
}

.category-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.model-tag {
  background: #374151;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  color: #d1d5db;
}

/* Loaded Models */
.loaded-models {
  background: #1f2937;
  border-radius: 10px;
  padding: 12px;
}

.loaded-model {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.loaded-name {
  color: #22c55e;
}

.loaded-size {
  color: #9ca3af;
}

/* Management Tab */
.manage-tab {
  padding-bottom: calc(100px + var(--sab, 0px));
}

.error-banner {
  background: #7f1d1d;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.error-close {
  background: none;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
}

/* Trinity Section */
.trinity-section {
  background: linear-gradient(135deg, rgba(147, 51, 234, 0.2) 0%, rgba(31, 41, 55, 1) 100%);
  border: 1px solid rgba(147, 51, 234, 0.3);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
}

.trinity-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.trinity-logo {
  width: 28px;
  height: 28px;
  filter: invert(70%) sepia(50%) saturate(500%) hue-rotate(220deg);
}

.trinity-title {
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.trinity-version {
  font-size: 10px;
  color: #9ca3af;
  font-family: monospace;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.trinity-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.trinity-update-btn {
  flex: 1;
  padding: 10px;
  background: #7c3aed;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.trinity-update-btn:disabled {
  background: #4b5563;
  cursor: wait;
}

.trinity-restart-btn {
  padding: 10px 16px;
  background: #374151;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
}

.trinity-result {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  margin-bottom: 10px;
}

.trinity-result.success {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.trinity-result.error {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.trinity-services {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trinity-service {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: rgba(55, 65, 81, 0.5);
  border-radius: 6px;
}

.trinity-service-name {
  color: #e5e7eb;
  font-size: 13px;
  text-transform: capitalize;
}

.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.services-list,
.containers-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.service-card,
.container-card {
  background: #1f2937;
  border-radius: 12px;
  padding: 14px;
}

.service-header,
.container-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.service-title,
.container-name {
  font-weight: 600;
  font-size: 14px;
}

.service-desc,
.container-image {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 10px;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.status-running {
  background: #14532d;
  color: #4ade80;
}

.status-stopped {
  background: #7f1d1d;
  color: #f87171;
}

.status-unknown {
  background: #374151;
  color: #9ca3af;
}

.service-actions,
.container-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  color: white;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.start {
  background: #15803d;
}

.action-btn.stop {
  background: #b91c1c;
}

.action-btn.restart {
  background: #2563eb;
}

.action-btn.logs {
  background: #4b5563;
}

/* Empty & Loading States */
.empty-state {
  text-align: center;
  color: #6b7280;
  padding: 40px 20px;
}

.loading {
  text-align: center;
  color: #9ca3af;
  padding: 40px;
}

.refresh-btn {
  width: 100%;
  background: #374151;
  border: none;
  border-radius: 12px;
  padding: 14px;
  color: white;
  font-size: 14px;
  cursor: pointer;
  margin-top: 16px;
}

/* Bottom Navigation */
.mobile-nav {
  flex-shrink: 0;
  display: flex;
  background: #1f2937;
  border-top: 1px solid #374151;
  padding: 6px 0 calc(6px + var(--sab, 0px));
  transition: transform 0.2s ease-out;
}

.mobile-nav.nav-hidden {
  transform: translateY(100%);
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.nav-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  background: none;
  border: none;
  padding: 6px;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.nav-btn.active {
  color: #3b82f6;
}

.nav-icon {
  font-size: 22px;
}

.nav-label {
  font-size: 10px;
  font-weight: 500;
}

/* Logs Modal */
.logs-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  z-index: 100;
  display: flex;
  flex-direction: column;
  padding: calc(var(--sat, 0px) + 16px) 16px calc(var(--sab, 0px) + 16px);
}

.logs-content {
  flex: 1;
  background: #1f2937;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #374151;
  font-weight: 600;
}

.logs-close {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 24px;
  cursor: pointer;
}

.logs-text {
  flex: 1;
  overflow: auto;
  padding: 12px;
  font-size: 11px;
  font-family: monospace;
  color: #d1d5db;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* uPlot chart styling */
:deep(.uplot) {
  width: 100% !important;
}

:deep(.u-wrap) {
  width: 100% !important;
}

:deep(.u-over),
:deep(.u-under) {
  width: 100% !important;
}

/* Streaming and Resume styles for Agent */
.typing-label {
  margin-left: 8px;
  font-size: 11px;
  color: #9ca3af;
}

.streaming-text {
  display: inline;
}

.streaming-cursor {
  display: inline;
  animation: blink 1s infinite;
  color: #60a5fa;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-meta-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  margin-left: 16px;
  flex-wrap: wrap;
}

.tools-badge {
  font-size: 10px;
  color: #a78bfa;
  background: #2e1065;
  padding: 2px 6px;
  border-radius: 4px;
}

.resume-banner-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #422006;
  border-top: 1px solid #854d0e;
}

.resume-text-mobile {
  flex: 1;
  font-size: 12px;
  color: #fbbf24;
}

.resume-btn-mobile {
  background: #d97706;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.dismiss-btn-mobile {
  background: transparent;
  border: none;
  color: #fbbf24;
  font-size: 18px;
  padding: 4px 8px;
}

.cancel-btn-mobile {
  width: 44px;
  height: 44px;
  background: #dc2626;
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

/* Rick-only mode (no tab bar) */
.rick-only-header {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
}

.rick-only-content .tab-content {
  padding-bottom: 16px;
}

.rick-only-content .rick-tab {
  padding-bottom: calc(80px + var(--sab, 0px));
}
</style>
