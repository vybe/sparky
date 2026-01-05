import { ref, nextTick } from 'vue'

export function useAgent(apiBaseUrl) {
  const agentMessages = ref([])
  const agentInput = ref('')
  const agentLoading = ref(false)
  const agentSessionId = ref(null)
  const agentContainer = ref(null)
  const agentStatus = ref(null)
  const agentTotalCost = ref(0)

  // Session management
  const savedSessions = ref([])
  const showSessionPicker = ref(false)
  const agentSessionName = ref('')

  async function checkAgentStatus() {
    try {
      const res = await fetch(`${apiBaseUrl}/claude/status`)
      agentStatus.value = await res.json()
    } catch (e) {
      agentStatus.value = { available: false, error: e.message }
    }
  }

  async function loadSessions() {
    try {
      const res = await fetch(`${apiBaseUrl}/claude/sessions`)
      const data = await res.json()
      savedSessions.value = data.sessions || []
    } catch (e) {
      console.error('Failed to load sessions:', e)
    }
  }

  async function saveAgentSession() {
    if (!agentSessionId.value) return

    const name = agentSessionName.value.trim() || `Session ${new Date().toLocaleString()}`
    const firstMsg = agentMessages.value.find(m => m.role === 'user')?.content || ''

    try {
      await fetch(`${apiBaseUrl}/claude/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: agentSessionId.value,
          name: name,
          first_message: firstMsg.slice(0, 100)
        })
      })
      agentSessionName.value = name
      await loadSessions()
    } catch (e) {
      console.error('Failed to save session:', e)
    }
  }

  async function loadAgentSession(session) {
    agentSessionId.value = session.session_id
    agentSessionName.value = session.name
    agentMessages.value = []
    agentTotalCost.value = 0
    showSessionPicker.value = false

    agentMessages.value.push({
      role: 'assistant',
      content: `📂 Resumed: "${session.name}"\n\n${session.first_message || ''}`,
      isSystem: true
    })
  }

  async function deleteAgentSession(session, event) {
    event.stopPropagation()
    if (!confirm(`Delete "${session.name}"?`)) return

    try {
      await fetch(`${apiBaseUrl}/claude/sessions/${session.session_id}`, { method: 'DELETE' })
      await loadSessions()
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  async function sendAgentMessage() {
    if (!agentInput.value.trim() || agentLoading.value) return

    const userMessage = agentInput.value.trim()
    agentInput.value = ''

    agentMessages.value.push({ role: 'user', content: userMessage })
    agentMessages.value.push({ role: 'assistant', content: '', loading: true })

    await scrollAgentToBottom()
    agentLoading.value = true

    try {
      const payload = {
        message: userMessage,
        session_id: agentSessionId.value
      }

      const res = await fetch(`${apiBaseUrl}/claude/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Request failed')
      }

      const data = await res.json()
      const lastMsg = agentMessages.value[agentMessages.value.length - 1]
      lastMsg.loading = false
      lastMsg.content = data.result
      lastMsg.duration = data.duration_ms
      lastMsg.cost = data.cost_usd

      const isNewSession = !agentSessionId.value && data.session_id
      if (data.session_id) {
        agentSessionId.value = data.session_id
      }
      agentTotalCost.value += data.cost_usd || 0

      if (isNewSession) {
        await saveAgentSession()
      }

      await scrollAgentToBottom()

    } catch (e) {
      const lastMsg = agentMessages.value[agentMessages.value.length - 1]
      lastMsg.loading = false
      lastMsg.content = `Error: ${e.message}`
      lastMsg.isError = true
    } finally {
      agentLoading.value = false
    }
  }

  async function scrollAgentToBottom() {
    await nextTick()
    if (agentContainer.value) {
      agentContainer.value.scrollTop = agentContainer.value.scrollHeight
    }
  }

  function clearAgent() {
    agentMessages.value = []
    agentSessionId.value = null
    agentSessionName.value = ''
    agentTotalCost.value = 0
  }

  return {
    // State
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
    // Methods
    checkAgentStatus,
    loadSessions,
    saveAgentSession,
    loadAgentSession,
    deleteAgentSession,
    sendAgentMessage,
    clearAgent
  }
}
