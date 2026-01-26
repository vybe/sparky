import { ref, nextTick, onUnmounted } from 'vue'

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

  // Streaming state
  const currentStreamController = ref(null)
  const streamingText = ref('')
  const currentTool = ref(null)
  const lastFailedSessionId = ref(null)

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
    lastFailedSessionId.value = null

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

  // Send message with streaming
  async function sendAgentMessage() {
    if (!agentInput.value.trim() || agentLoading.value) return

    const userMessage = agentInput.value.trim()
    agentInput.value = ''

    // Clear any previous failed session tracking
    lastFailedSessionId.value = null

    // Add user message
    agentMessages.value.push({ role: 'user', content: userMessage })

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
    agentMessages.value.push(assistantMsg)
    await scrollAgentToBottom()

    agentLoading.value = true
    streamingText.value = ''
    currentTool.value = null

    // Create abort controller for cancellation
    const abortController = new AbortController()
    currentStreamController.value = abortController

    try {
      const payload = {
        message: userMessage,
        session_id: agentSessionId.value
      }

      const res = await fetch(`${apiBaseUrl}/claude/chat/stream`, {
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
      let receivedSessionId = agentSessionId.value
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
              agentSessionId.value = event.session_id
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
                await scrollAgentToBottom()
                break

              case 'tool_use':
                // Claude is using a tool
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
                agentTotalCost.value += event.cost_usd || 0
                if (event.session_id) {
                  agentSessionId.value = event.session_id
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
                  agentSessionId.value = event.session_id
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

      // Auto-save and auto-name new sessions
      const isNewSession = !agentSessionName.value && receivedSessionId
      if (isNewSession) {
        agentSessionId.value = receivedSessionId
        // Ask Claude to generate a meaningful session name
        try {
          const nameRes = await fetch(`${apiBaseUrl}/claude/name-session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              first_message: userMessage,
              session_id: receivedSessionId
            })
          })
          const nameData = await nameRes.json()
          if (nameData.success && nameData.name) {
            agentSessionName.value = nameData.name
          }
        } catch (e) {
          // Fallback to truncated message
          agentSessionName.value = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '')
        }
        await saveAgentSession()
      }

      await scrollAgentToBottom()

    } catch (e) {
      const lastMsg = agentMessages.value[agentMessages.value.length - 1]
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
        if (agentSessionId.value) {
          lastFailedSessionId.value = agentSessionId.value
        }
      }
    } finally {
      agentLoading.value = false
      currentStreamController.value = null
      streamingText.value = ''
      currentTool.value = null
    }
  }

  // Cancel current streaming request
  function cancelAgentStream() {
    if (currentStreamController.value) {
      currentStreamController.value.abort()
    }
  }

  // Resume last failed session
  async function resumeLastSession() {
    const resumeSessionId = lastFailedSessionId.value || agentSessionId.value
    if (!resumeSessionId) return

    // Set the session and ask what happened
    agentSessionId.value = resumeSessionId
    agentInput.value = 'What was the result of the previous task? Please summarize what you did.'
    lastFailedSessionId.value = null
    await sendAgentMessage()
  }

  async function scrollAgentToBottom() {
    await nextTick()
    if (agentContainer.value) {
      agentContainer.value.scrollTop = agentContainer.value.scrollHeight
    }
  }

  function clearAgent() {
    // Cancel any ongoing stream
    if (currentStreamController.value) {
      currentStreamController.value.abort()
    }
    agentMessages.value = []
    agentSessionId.value = null
    agentSessionName.value = ''
    agentTotalCost.value = 0
    lastFailedSessionId.value = null
    streamingText.value = ''
  }

  // Cleanup on unmount
  function cleanup() {
    if (currentStreamController.value) {
      currentStreamController.value.abort()
    }
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
    // Streaming state
    currentTool,
    lastFailedSessionId,
    // Methods
    checkAgentStatus,
    loadSessions,
    saveAgentSession,
    loadAgentSession,
    deleteAgentSession,
    sendAgentMessage,
    cancelAgentStream,
    resumeLastSession,
    clearAgent,
    cleanup
  }
}
