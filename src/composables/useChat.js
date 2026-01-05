import { ref, watch, nextTick } from 'vue'
import { useConfig } from '../config.js'

const { ollamaUrl: OLLAMA_URL } = useConfig()

export function useChat() {
  const chatModels = ref([])
  const selectedChatModel = ref('')
  const chatMessages = ref([])
  const chatInput = ref('')
  const chatLoading = ref(false)
  const chatContainer = ref(null)
  const loadedModels = ref([])
  const modelLoadingState = ref('') // '' | 'loading' | 'loaded'
  const modelLoadProgress = ref('')
  const chatModelsError = ref('')
  const chatModelsLoading = ref(false)

  async function loadChatModels() {
    chatModelsLoading.value = true
    chatModelsError.value = ''
    try {
      const res = await fetch(`${OLLAMA_URL}/api/tags`, {
        signal: AbortSignal.timeout(5000)
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }
      const data = await res.json()
      chatModels.value = data.models || []
      if (chatModels.value.length === 0) {
        chatModelsError.value = 'No models found on server'
      } else if (!selectedChatModel.value) {
        const preferred = chatModels.value.find(m => m.name.includes('7b') || m.name.includes('8b'))
        selectedChatModel.value = preferred?.name || chatModels.value[0].name
      }
      await checkLoadedModels()
    } catch (e) {
      console.error('Failed to load models:', e)
      chatModelsError.value = `Cannot connect to Ollama. Check if Ollama is running in the Manage tab.`
    } finally {
      chatModelsLoading.value = false
    }
  }

  async function checkLoadedModels() {
    try {
      const res = await fetch(`${OLLAMA_URL}/api/ps`)
      const data = await res.json()
      loadedModels.value = (data.models || []).map(m => m.name)
    } catch (e) {
      loadedModels.value = []
    }
  }

  function isModelLoaded(modelName) {
    return loadedModels.value.includes(modelName)
  }

  async function loadSelectedModel() {
    if (!selectedChatModel.value || modelLoadingState.value === 'loading') return

    modelLoadingState.value = 'loading'
    modelLoadProgress.value = 'Loading model...'

    try {
      const response = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedChatModel.value,
          prompt: 'hi',
          stream: true
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(l => l.trim())

        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.status) {
              modelLoadProgress.value = data.status
            }
          } catch (e) { /* skip */ }
        }
      }

      modelLoadingState.value = 'loaded'
      modelLoadProgress.value = ''
      await checkLoadedModels()
    } catch (e) {
      modelLoadingState.value = ''
      modelLoadProgress.value = `Error: ${e.message}`
      setTimeout(() => { modelLoadProgress.value = '' }, 3000)
    }
  }

  // Reset load state when model changes
  watch(selectedChatModel, () => {
    modelLoadingState.value = ''
    modelLoadProgress.value = ''
  })

  async function sendChat() {
    if (!chatInput.value.trim() || chatLoading.value) return

    const userMessage = chatInput.value.trim()
    chatInput.value = ''

    chatMessages.value.push({ role: 'user', content: userMessage })
    chatMessages.value.push({ role: 'assistant', content: '', loading: true })

    await scrollChatToBottom()
    chatLoading.value = true

    try {
      const response = await fetch(`${OLLAMA_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedChatModel.value,
          messages: chatMessages.value.filter(m => !m.loading).map(m => ({
            role: m.role,
            content: m.content
          })),
          stream: true
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      const assistantMessage = chatMessages.value[chatMessages.value.length - 1]
      assistantMessage.loading = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(l => l.trim())

        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.message?.content) {
              assistantMessage.content += data.message.content
              await scrollChatToBottom()
            }
          } catch (e) { /* skip */ }
        }
      }
    } catch (e) {
      chatMessages.value[chatMessages.value.length - 1].content = `Error: ${e.message}`
      chatMessages.value[chatMessages.value.length - 1].loading = false
    } finally {
      chatLoading.value = false
    }
  }

  async function scrollChatToBottom() {
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  }

  function clearChat() {
    chatMessages.value = []
  }

  async function unloadModel(modelName) {
    try {
      // Ollama doesn't have a direct unload API, but we can use the /api/generate endpoint
      // with an empty model to trigger cleanup, or just wait for automatic timeout (5 min)
      // For now, we'll just refresh the loaded models list
      await checkLoadedModels()
    } catch (e) {
      console.error('Failed to unload model:', e)
    }
  }

  return {
    // State
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
    // Methods
    loadChatModels,
    checkLoadedModels,
    isModelLoaded,
    loadSelectedModel,
    unloadModel,
    sendChat,
    clearChat
  }
}
