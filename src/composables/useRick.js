import { ref, nextTick } from 'vue'

export function useRick(apiBaseUrl) {
  const rickMessages = ref([])
  const rickInput = ref('')
  const rickLoading = ref(false)
  const rickSessionId = ref(null)
  const rickContainer = ref(null)
  const rickStatus = ref(null)
  const rickTotalCost = ref(0)

  // Session management
  const rickSavedSessions = ref([])
  const showRickSessionPicker = ref(false)
  const rickSessionName = ref('')

  // Streaming state
  const currentRickStreamController = ref(null)
  const rickStreamingText = ref('')
  const rickCurrentTool = ref(null)
  const rickLastFailedSessionId = ref(null)

  async function checkRickStatus() {
    try {
      const res = await fetch(`${apiBaseUrl}/rick/status`)
      rickStatus.value = await res.json()
    } catch (e) {
      rickStatus.value = { available: false, error: e.message }
    }
  }

  async function loadRickSessions() {
    try {
      const res = await fetch(`${apiBaseUrl}/rick/sessions`)
      const data = await res.json()
      rickSavedSessions.value = data.sessions || []
    } catch (e) {
      console.error('Failed to load Rick sessions:', e)
    }
  }

  async function saveRickSession() {
    if (!rickSessionId.value) return

    const name = rickSessionName.value.trim() || `Session ${new Date().toLocaleString()}`
    const firstMsg = rickMessages.value.find(m => m.role === 'user')?.content || ''

    try {
      await fetch(`${apiBaseUrl}/rick/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: rickSessionId.value,
          name: name,
          first_message: firstMsg.slice(0, 100)
        })
      })
      rickSessionName.value = name
      await loadRickSessions()
    } catch (e) {
      console.error('Failed to save Rick session:', e)
    }
  }

  async function loadRickSession(session) {
    rickSessionId.value = session.session_id
    rickSessionName.value = session.name
    rickMessages.value = []
    rickTotalCost.value = 0
    showRickSessionPicker.value = false
    rickLastFailedSessionId.value = null

    rickMessages.value.push({
      role: 'assistant',
      content: `📂 Resumed: "${session.name}"\n\n${session.first_message || ''}`,
      isSystem: true
    })
  }

  async function deleteRickSession(session, event) {
    event.stopPropagation()
    if (!confirm(`Delete "${session.name}"?`)) return

    try {
      await fetch(`${apiBaseUrl}/rick/sessions/${session.session_id}`, { method: 'DELETE' })
      await loadRickSessions()
    } catch (e) {
      console.error('Failed to delete Rick session:', e)
    }
  }

  // Send message with streaming
  async function sendRickMessage() {
    if (!rickInput.value.trim() || rickLoading.value) return

    const userMessage = rickInput.value.trim()
    rickInput.value = ''

    // Clear any previous failed session tracking
    rickLastFailedSessionId.value = null

    // Add user message
    rickMessages.value.push({ role: 'user', content: userMessage })

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
    rickMessages.value.push(assistantMsg)
    await scrollRickToBottom()

    rickLoading.value = true
    rickStreamingText.value = ''
    rickCurrentTool.value = null

    // Create abort controller for cancellation
    const abortController = new AbortController()
    currentRickStreamController.value = abortController

    try {
      const payload = {
        message: userMessage,
        session_id: rickSessionId.value
      }

      const res = await fetch(`${apiBaseUrl}/rick/chat/stream`, {
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
      let receivedSessionId = rickSessionId.value
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
              rickSessionId.value = event.session_id
            }

            switch (event.type) {
              case 'init':
                assistantMsg.content = '⏳ ' + (event.message || 'Starting...')
                break

              case 'message':
                rickStreamingText.value += event.text || ''
                assistantMsg.content = rickStreamingText.value
                assistantMsg.loading = false
                await scrollRickToBottom()
                break

              case 'tool_use':
                rickCurrentTool.value = event.tool
                if (!assistantMsg.tools.includes(event.tool)) {
                  assistantMsg.tools.push(event.tool)
                }
                if (!rickStreamingText.value.includes(`[Using ${event.tool}]`)) {
                  rickStreamingText.value += `\n[Using ${event.tool}...]\n`
                  assistantMsg.content = rickStreamingText.value
                }
                break

              case 'system':
                if (event.message && !rickStreamingText.value) {
                  assistantMsg.content = '💭 ' + event.message
                }
                break

              case 'result':
                finalResult = event
                assistantMsg.content = event.result || rickStreamingText.value
                assistantMsg.duration = event.duration_ms
                assistantMsg.cost = event.cost_usd
                rickTotalCost.value += event.cost_usd || 0
                if (event.session_id) {
                  rickSessionId.value = event.session_id
                }
                break

              case 'error':
                assistantMsg.content = `Error: ${event.error}`
                assistantMsg.isError = true
                if (event.session_id) {
                  rickLastFailedSessionId.value = event.session_id
                }
                break

              case 'done':
                assistantMsg.duration = assistantMsg.duration || event.duration_ms
                if (event.session_id) {
                  rickSessionId.value = event.session_id
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

      if (finalResult) {
        assistantMsg.content = finalResult.result || rickStreamingText.value || assistantMsg.content
      } else if (rickStreamingText.value) {
        assistantMsg.content = rickStreamingText.value
      }

      // Auto-save and auto-name new sessions
      const isNewSession = !rickSessionName.value && receivedSessionId
      if (isNewSession) {
        rickSessionId.value = receivedSessionId
        // Ask Claude to generate a meaningful session name
        try {
          const nameRes = await fetch(`${apiBaseUrl}/rick/name-session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              first_message: userMessage,
              session_id: receivedSessionId
            })
          })
          const nameData = await nameRes.json()
          if (nameData.success && nameData.name) {
            rickSessionName.value = nameData.name
          }
        } catch (e) {
          // Fallback to truncated message
          rickSessionName.value = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '')
        }
        await saveRickSession()
      }

      await scrollRickToBottom()

    } catch (e) {
      const lastMsg = rickMessages.value[rickMessages.value.length - 1]
      lastMsg.loading = false
      lastMsg.streaming = false

      if (e.name === 'AbortError') {
        lastMsg.content = rickStreamingText.value + '\n\n[Cancelled by user]'
      } else {
        lastMsg.content = rickStreamingText.value
          ? `${rickStreamingText.value}\n\n⚠️ Connection error: ${e.message}`
          : `Error: ${e.message}`
        lastMsg.isError = true

        if (rickSessionId.value) {
          rickLastFailedSessionId.value = rickSessionId.value
        }
      }
    } finally {
      rickLoading.value = false
      currentRickStreamController.value = null
      rickStreamingText.value = ''
      rickCurrentTool.value = null
    }
  }

  function cancelRickStream() {
    if (currentRickStreamController.value) {
      currentRickStreamController.value.abort()
    }
  }

  async function resumeRickLastSession() {
    const resumeSessionId = rickLastFailedSessionId.value || rickSessionId.value
    if (!resumeSessionId) return

    rickSessionId.value = resumeSessionId
    rickInput.value = 'What was the result of the previous task? Please summarize what you did.'
    rickLastFailedSessionId.value = null
    await sendRickMessage()
  }

  async function scrollRickToBottom() {
    await nextTick()
    if (rickContainer.value) {
      rickContainer.value.scrollTop = rickContainer.value.scrollHeight
    }
  }

  function clearRick() {
    if (currentRickStreamController.value) {
      currentRickStreamController.value.abort()
    }
    rickMessages.value = []
    rickSessionId.value = null
    rickSessionName.value = ''
    rickTotalCost.value = 0
    rickLastFailedSessionId.value = null
    rickStreamingText.value = ''
  }

  function cleanupRick() {
    if (currentRickStreamController.value) {
      currentRickStreamController.value.abort()
    }
  }

  return {
    // State
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
    // Streaming state
    rickCurrentTool,
    rickLastFailedSessionId,
    // Methods
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
  }
}
