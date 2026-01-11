<script setup>
import { onMounted } from 'vue'
import { useChat } from '../composables/useChat.js'

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
} = useChat()

onMounted(async () => {
  await loadChatModels()
  // Poll loaded models every 10 seconds
  setInterval(checkLoadedModels, 10000)
})

function formatSize(bytes) {
  if (!bytes) return ''
  const gb = bytes / (1024 * 1024 * 1024)
  return `${gb.toFixed(1)}GB`
}

function formatParamSize(paramSize) {
  if (!paramSize) return ''
  return paramSize
}

async function handleSend() {
  await sendChat()
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-200px)]">
    <!-- Header -->
    <div class="bg-gray-800 rounded-lg p-4 mb-4">
      <div class="flex items-center gap-4 mb-3">
        <div class="flex-1 flex items-center gap-2">
          <select
            v-model="selectedChatModel"
            class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            :disabled="chatModelsLoading || chatModels.length === 0"
          >
            <option v-if="chatModels.length === 0" value="">
              {{ chatModelsLoading ? 'Loading models...' : 'No models available' }}
            </option>
            <option v-for="model in chatModels" :key="model.name" :value="model.name">
              {{ model.name }}
              <span v-if="formatParamSize(model.details?.parameter_size)">
                ({{ formatParamSize(model.details.parameter_size) }})
              </span>
              {{ isModelLoaded(model.name) ? ' ✓ Loaded' : '' }}
            </option>
          </select>

          <!-- Load button -->
          <button
            v-if="!isModelLoaded(selectedChatModel) && selectedChatModel"
            @click="loadSelectedModel"
            :disabled="modelLoadingState === 'loading'"
            class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
            title="Load model into memory"
          >
            {{ modelLoadingState === 'loading' ? '⏳ Loading...' : '📥 Load Model' }}
          </button>

          <!-- Loaded indicator -->
          <div
            v-else-if="selectedChatModel && isModelLoaded(selectedChatModel)"
            class="px-4 py-2 bg-green-900 rounded text-sm text-green-300 flex items-center gap-2"
          >
            <span class="text-green-400">✓</span> Loaded in Memory
          </div>
        </div>

        <button
          @click="clearChat"
          class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
          title="Clear chat history"
        >
          🗑️ Clear
        </button>

        <button
          @click="loadChatModels"
          class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
          title="Refresh model list"
        >
          🔄 Refresh
        </button>
      </div>

      <!-- Model loading progress -->
      <div v-if="modelLoadProgress" class="text-sm text-blue-400 animate-pulse">
        {{ modelLoadProgress }}
      </div>

      <!-- Warning if model not loaded -->
      <div
        v-if="!isModelLoaded(selectedChatModel) && modelLoadingState !== 'loading' && selectedChatModel"
        class="text-sm text-yellow-400 flex items-center gap-2 bg-yellow-900/20 rounded px-3 py-2"
      >
        <span>⚠️</span>
        <span>Model not loaded in memory. Click "📥 Load Model" first (large models take 30-90s to load).</span>
      </div>

      <!-- Error message -->
      <div v-if="chatModelsError" class="text-sm text-red-400 flex items-center gap-2 bg-red-900/20 rounded px-3 py-2">
        <span>❌</span>
        <span>{{ chatModelsError }}</span>
      </div>

      <!-- Currently loaded models info -->
      <div v-if="loadedModels.length > 0" class="mt-3 pt-3 border-t border-gray-700">
        <div class="text-xs text-gray-400 mb-1">Currently in Memory ({{ loadedModels.length }}):</div>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="model in loadedModels"
            :key="model"
            class="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300"
          >
            {{ model }}
          </span>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div
      ref="chatContainer"
      class="flex-1 overflow-y-auto bg-gray-800 rounded-lg p-4 space-y-4"
    >
      <div v-if="chatMessages.length === 0" class="text-center text-gray-500 py-8">
        Start a conversation with {{ selectedChatModel || 'an AI model' }}
      </div>

      <div
        v-for="(msg, idx) in chatMessages"
        :key="idx"
        :class="[
          'max-w-3xl',
          msg.role === 'user' ? 'ml-auto' : 'mr-auto'
        ]"
      >
        <div
          :class="[
            'rounded-lg px-4 py-3',
            msg.role === 'user'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-100'
          ]"
        >
          <div v-if="msg.loading" class="flex items-center gap-2">
            <span class="animate-pulse">●</span>
            <span class="animate-pulse delay-100">●</span>
            <span class="animate-pulse delay-200">●</span>
          </div>
          <div v-else class="whitespace-pre-wrap">{{ msg.content }}</div>
        </div>
        <div
          :class="[
            'text-xs text-gray-500 mt-1',
            msg.role === 'user' ? 'text-right' : 'text-left'
          ]"
        >
          {{ msg.role === 'user' ? 'You' : selectedChatModel }}
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="mt-4 flex gap-2">
      <textarea
        v-model="chatInput"
        @keydown.enter.exact.prevent="handleSend"
        placeholder="Type a message... (Enter to send)"
        rows="2"
        inputmode="text"
        autocomplete="off"
        autocorrect="on"
        autocapitalize="sentences"
        spellcheck="true"
        class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 text-base touch-manipulation"
        style="font-size: 16px;"
      ></textarea>
      <button
        @click="handleSend"
        :disabled="chatLoading || !chatInput.trim() || !isModelLoaded(selectedChatModel)"
        class="px-6 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors touch-manipulation"
        title="Send message (model must be loaded first)"
      >
        {{ chatLoading ? '...' : 'Send' }}
      </button>
    </div>
  </div>
</template>
