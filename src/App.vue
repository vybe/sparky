<script setup>
import { ref, computed, onMounted } from 'vue'
import Dashboard from './components/Dashboard.vue'
import ImageGenerator from './components/ImageGenerator.vue'
import Chat from './components/Chat.vue'
import VideoGenerator from './components/VideoGenerator.vue'
import VoiceChat from './components/VoiceChat.vue'
import ActivityMonitor from './components/ActivityMonitor.vue'
import Management from './components/Management.vue'
import AgentChat from './components/AgentChat.vue'
import GooseChat from './components/GooseChat.vue'
import RickChat from './components/RickChat.vue'
import Mobile from './components/Mobile.vue'

// Check if mobile mode is requested via URL param or if on small screen
const isMobileMode = ref(false)

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  // Check for ?mobile=1 or if running as standalone PWA
  const mobileParam = params.get('mobile') === '1'
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                       window.navigator.standalone === true
  isMobileMode.value = mobileParam || isStandalone
})

const activeTab = ref('dashboard')
const tabs = [
  { id: 'dashboard', name: 'Overview', icon: '⚡' },
  { id: 'agent', name: 'Agent', icon: '🤖' },
  { id: 'rick', name: 'Rick', icon: '🧑‍💼' },
  { id: 'goose', name: 'Goose', icon: '🪿' },
  { id: 'chat', name: 'Chat', icon: '💬' },
  { id: 'image', name: 'Image Gen', icon: '🎨' },
  { id: 'video', name: 'Video Gen', icon: '🎬' },
  { id: 'voice', name: 'Voice', icon: '🎤' },
  { id: 'manage', name: 'Manage', icon: '⚙️' },
]

// Allow switching between desktop and mobile mode
function toggleMode() {
  isMobileMode.value = !isMobileMode.value
  // Update URL without reload
  const url = new URL(window.location.href)
  if (isMobileMode.value) {
    url.searchParams.set('mobile', '1')
  } else {
    url.searchParams.delete('mobile')
  }
  window.history.replaceState({}, '', url)
}
</script>

<template>
  <!-- Mobile Mode -->
  <Mobile v-if="isMobileMode" />

  <!-- Desktop Mode -->
  <div v-else class="min-h-screen bg-gray-900 text-gray-100">
    <!-- Header -->
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-3">
      <div class="max-w-7xl mx-auto">
        <div class="flex items-center justify-between mb-3">
          <h1 class="text-xl font-bold text-white">Sparky</h1>
          <div class="flex items-center gap-4">
            <button
              @click="toggleMode"
              class="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
              title="Switch to mobile view"
            >
              📱 Mobile
            </button>
            <div class="flex items-center gap-2 text-sm text-gray-400">
              <span class="w-2 h-2 bg-green-500 rounded-full"></span>
              Connected via tunnel
            </div>
          </div>
        </div>
        <ActivityMonitor />
      </div>
    </header>

    <!-- Tabs -->
    <nav class="bg-gray-800/50 border-b border-gray-700">
      <div class="max-w-7xl mx-auto px-6">
        <div class="flex gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'text-white border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white'
            ]"
          >
            <span class="mr-2">{{ tab.icon }}</span>
            {{ tab.name }}
          </button>
        </div>
      </div>
    </nav>

    <!-- Content - keep-alive preserves component state when switching tabs -->
    <main class="max-w-7xl mx-auto p-6">
      <keep-alive>
        <Dashboard v-if="activeTab === 'dashboard'" />
      </keep-alive>
      <keep-alive>
        <AgentChat v-if="activeTab === 'agent'" />
      </keep-alive>
      <keep-alive>
        <RickChat v-if="activeTab === 'rick'" />
      </keep-alive>
      <keep-alive>
        <GooseChat v-if="activeTab === 'goose'" />
      </keep-alive>
      <keep-alive>
        <ImageGenerator v-if="activeTab === 'image'" />
      </keep-alive>
      <keep-alive>
        <VideoGenerator v-if="activeTab === 'video'" />
      </keep-alive>
      <keep-alive>
        <Chat v-if="activeTab === 'chat'" />
      </keep-alive>
      <keep-alive>
        <VoiceChat v-if="activeTab === 'voice'" />
      </keep-alive>
      <keep-alive>
        <Management v-if="activeTab === 'manage'" />
      </keep-alive>
    </main>
  </div>
</template>
