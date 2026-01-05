<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const services = ref([])
const containers = ref([])
const systemInfo = ref(null)
const gpuStats = ref(null)
const diskStats = ref(null)
const processes = ref({ top_cpu: [], top_memory: [], gpu_processes: [] })
const trinity = ref({ services: [], version: null })
const trinityUpdating = ref(false)
const trinityUpdateResult = ref(null)
const loading = ref(true)
const actionLoading = ref({})
const logs = ref({ container: null, content: '', visible: false })
const error = ref(null)

let refreshInterval = null

async function fetchApi(endpoint, options = {}) {
  const res = await fetch(`/api${endpoint}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers }
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

async function loadAll() {
  try {
    error.value = null
    const [servicesData, containersData, infoData, gpuData, diskData, processData, trinityData] = await Promise.all([
      fetchApi('/services'),
      fetchApi('/containers?all=true'),
      fetchApi('/info'),
      fetchApi('/gpu').catch(() => null),
      fetchApi('/disk').catch(() => null),
      fetchApi('/processes?limit=8').catch(() => ({ top_cpu: [], top_memory: [], gpu_processes: [] })),
      fetchApi('/trinity/status').catch(() => ({ services: [], version: null }))
    ])
    // Filter out Trinity services from the regular services list
    services.value = servicesData.services.filter(s => !s.name.startsWith('trinity-'))
    containers.value = containersData.containers
    systemInfo.value = infoData
    gpuStats.value = gpuData
    diskStats.value = diskData
    processes.value = processData
    trinity.value = trinityData
  } catch (e) {
    error.value = e.message
    console.error('Failed to load data:', e)
  } finally {
    loading.value = false
  }
}

async function updateTrinity() {
  if (trinityUpdating.value) return
  trinityUpdating.value = true
  trinityUpdateResult.value = null
  try {
    const result = await fetchApi('/trinity/update', { method: 'POST' })
    trinityUpdateResult.value = result
    if (result.success) {
      // Reload Trinity status after update
      const trinityData = await fetchApi('/trinity/status').catch(() => ({ services: [], version: null }))
      trinity.value = trinityData
    }
  } catch (e) {
    trinityUpdateResult.value = { success: false, error: e.message }
  } finally {
    trinityUpdating.value = false
  }
}

async function restartTrinity() {
  actionLoading.value['trinity-restart'] = true
  try {
    await fetchApi('/trinity/restart', { method: 'POST' })
    await loadAll()
  } catch (e) {
    error.value = `Failed to restart Trinity: ${e.message}`
  } finally {
    actionLoading.value['trinity-restart'] = false
  }
}

async function performAction(containerName, action) {
  const key = `${containerName}-${action}`
  actionLoading.value[key] = true
  try {
    await fetchApi(`/containers/${containerName}/action`, {
      method: 'POST',
      body: JSON.stringify({ action })
    })
    // Refresh after action
    await loadAll()
  } catch (e) {
    error.value = `Failed to ${action} ${containerName}: ${e.message}`
  } finally {
    actionLoading.value[key] = false
  }
}

async function restartService(serviceName) {
  actionLoading.value[`service-${serviceName}`] = true
  try {
    await fetchApi(`/services/${serviceName}/restart`, { method: 'POST' })
    await loadAll()
  } catch (e) {
    error.value = `Failed to restart ${serviceName}: ${e.message}`
  } finally {
    actionLoading.value[`service-${serviceName}`] = false
  }
}

async function viewLogs(containerName) {
  logs.value = { container: containerName, content: 'Loading...', visible: true }
  try {
    const data = await fetchApi(`/containers/${containerName}/logs?lines=200`)
    logs.value.content = data.logs || 'No logs available'
  } catch (e) {
    logs.value.content = `Error: ${e.message}`
  }
}

function closeLogs() {
  logs.value = { container: null, content: '', visible: false }
}

function getStatusColor(status) {
  switch (status) {
    case 'running': return 'text-green-400'
    case 'exited': return 'text-red-400'
    case 'paused': return 'text-yellow-400'
    case 'not found': return 'text-gray-500'
    default: return 'text-gray-400'
  }
}

function getStatusBg(status) {
  switch (status) {
    case 'running': return 'bg-green-500/20'
    case 'exited': return 'bg-red-500/20'
    default: return 'bg-gray-500/20'
  }
}

onMounted(() => {
  loadAll()
  refreshInterval = setInterval(loadAll, 15000) // Refresh every 15s
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Error Banner -->
    <div v-if="error" class="bg-red-500/20 border border-red-500 rounded-lg p-4 flex items-center justify-between">
      <span class="text-red-400">{{ error }}</span>
      <button @click="error = null" class="text-red-400 hover:text-red-300">&times;</button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      <span class="ml-3 text-gray-400">Loading system info...</span>
    </div>

    <template v-else>
      <!-- System Overview -->
      <section class="bg-gray-800 rounded-xl p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-white flex items-center gap-2">
            <span>🖥️</span> System Overview
          </h2>
          <button
            @click="loadAll"
            class="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            ↻ Refresh
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Docker Info -->
          <div v-if="systemInfo" class="bg-gray-700/50 rounded-lg p-4">
            <div class="text-gray-400 text-sm mb-1">Docker</div>
            <div class="text-white font-medium">v{{ systemInfo.docker_version }}</div>
            <div class="text-gray-500 text-xs mt-1">
              {{ systemInfo.containers_running }}/{{ systemInfo.containers_total }} containers
            </div>
            <div class="text-gray-500 text-xs">{{ systemInfo.images }} images</div>
          </div>

          <!-- GPU Stats -->
          <div v-if="gpuStats" class="bg-gray-700/50 rounded-lg p-4">
            <div class="text-gray-400 text-sm mb-1">GPU</div>
            <div class="text-white font-medium">{{ gpuStats.utilization_percent }}% utilized</div>
            <div class="text-gray-500 text-xs mt-1">
              {{ Math.round(gpuStats.memory_used_mb / 1024) }}GB / {{ Math.round(gpuStats.memory_total_mb / 1024) }}GB
            </div>
            <div class="text-gray-500 text-xs">{{ gpuStats.temperature_c }}°C · {{ gpuStats.power_draw_w }}W</div>
          </div>

          <!-- Memory -->
          <div v-if="systemInfo" class="bg-gray-700/50 rounded-lg p-4">
            <div class="text-gray-400 text-sm mb-1">Host Memory</div>
            <div class="text-white font-medium">{{ systemInfo.memory_total_gb }} GB</div>
            <div class="text-gray-500 text-xs mt-1">{{ systemInfo.cpus }} CPUs ({{ systemInfo.architecture }})</div>
          </div>

          <!-- Disk -->
          <div v-if="diskStats" class="bg-gray-700/50 rounded-lg p-4">
            <div class="text-gray-400 text-sm mb-1">Disk</div>
            <div class="text-white font-medium">{{ diskStats.use_percent }} used</div>
            <div class="text-gray-500 text-xs mt-1">{{ diskStats.available }} available</div>
            <div class="text-gray-500 text-xs">{{ diskStats.size }} total</div>
          </div>
        </div>
      </section>

      <!-- Top Processes -->
      <section class="bg-gray-800 rounded-xl p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span>📊</span> Top Processes
        </h2>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <!-- GPU Processes -->
          <div class="bg-gray-700/50 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-green-400">🎮</span>
              <span class="text-gray-300 font-medium">GPU Memory</span>
            </div>
            <div v-if="processes.gpu_processes?.length" class="space-y-2">
              <div
                v-for="p in processes.gpu_processes"
                :key="p.pid"
                class="flex justify-between items-center text-sm"
              >
                <span class="text-gray-300 truncate" :title="p.name">{{ p.name }}</span>
                <span class="text-green-400 font-mono ml-2">{{ (p.gpu_memory_mb / 1024).toFixed(1) }}GB</span>
              </div>
            </div>
            <div v-else class="text-gray-500 text-sm italic">No GPU processes</div>
          </div>

          <!-- Top Memory -->
          <div class="bg-gray-700/50 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-blue-400">🧠</span>
              <span class="text-gray-300 font-medium">Memory Usage</span>
            </div>
            <div class="space-y-3">
              <div
                v-for="p in processes.top_memory?.slice(0, 3)"
                :key="p.pid"
                class="text-sm"
              >
                <div class="flex justify-between items-center">
                  <span class="text-gray-200 font-medium">{{ p.name }}</span>
                  <span class="text-blue-400 font-mono">{{ (p.memory_mb / 1024).toFixed(1) }}GB</span>
                </div>
                <div class="text-gray-500 text-xs truncate mt-0.5" :title="p.cmdline">{{ p.cmdline }}</div>
              </div>
            </div>
          </div>

          <!-- Top CPU -->
          <div class="bg-gray-700/50 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-yellow-400">💻</span>
              <span class="text-gray-300 font-medium">CPU Usage</span>
            </div>
            <div class="space-y-3">
              <div
                v-for="p in processes.top_cpu?.slice(0, 3)"
                :key="p.pid"
                class="text-sm"
              >
                <div class="flex justify-between items-center">
                  <span class="text-gray-200 font-medium">{{ p.name }}</span>
                  <span class="text-yellow-400 font-mono">{{ p.cpu_percent }}%</span>
                </div>
                <div class="text-gray-500 text-xs truncate mt-0.5" :title="p.cmdline">{{ p.cmdline }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Trinity Agent Platform -->
      <section class="bg-gradient-to-br from-purple-900/40 to-gray-800 rounded-xl p-6 border border-purple-500/30">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <img src="/trinity-logo.svg" alt="Trinity" class="w-8 h-8 text-purple-400" style="filter: invert(70%) sepia(50%) saturate(500%) hue-rotate(220deg);" />
            <div>
              <h2 class="text-lg font-semibold text-white">Trinity Agent Platform</h2>
              <div v-if="trinity.version" class="text-xs text-gray-400 font-mono mt-0.5">{{ trinity.version }}</div>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              @click="updateTrinity"
              :disabled="trinityUpdating"
              class="px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-500 disabled:bg-gray-600 disabled:cursor-wait rounded transition-colors flex items-center gap-2"
            >
              <span v-if="trinityUpdating" class="animate-spin">↻</span>
              <span v-else>⬆</span>
              {{ trinityUpdating ? 'Updating...' : 'Update from GitHub' }}
            </button>
            <button
              @click="restartTrinity"
              :disabled="actionLoading['trinity-restart']"
              class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 rounded transition-colors"
            >
              {{ actionLoading['trinity-restart'] ? '...' : '↻ Restart All' }}
            </button>
          </div>
        </div>

        <!-- Update Result -->
        <div v-if="trinityUpdateResult" class="mb-4 p-3 rounded-lg" :class="trinityUpdateResult.success ? 'bg-green-500/20 border border-green-500/50' : 'bg-red-500/20 border border-red-500/50'">
          <div class="flex items-center gap-2">
            <span>{{ trinityUpdateResult.success ? '✓' : '✗' }}</span>
            <span :class="trinityUpdateResult.success ? 'text-green-400' : 'text-red-400'">
              {{ trinityUpdateResult.success ? 'Update completed successfully' : trinityUpdateResult.error }}
            </span>
          </div>
          <div v-if="trinityUpdateResult.version" class="text-xs text-gray-400 mt-1">New version: {{ trinityUpdateResult.version }}</div>
        </div>

        <!-- Trinity Services Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="service in trinity.services"
            :key="service.name"
            class="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="text-white font-medium capitalize">{{ service.name }}</div>
              <span
                :class="['px-2 py-0.5 rounded text-xs font-medium', getStatusBg(service.status), getStatusColor(service.status)]"
              >
                {{ service.status }}
              </span>
            </div>
            <div class="flex gap-2 mt-3">
              <button
                @click="restartService(`trinity-${service.name}`)"
                :disabled="actionLoading[`service-trinity-${service.name}`] || service.status === 'not found'"
                class="flex-1 px-3 py-1.5 bg-purple-600/50 hover:bg-purple-500/50 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-xs text-white transition-colors"
              >
                {{ actionLoading[`service-trinity-${service.name}`] ? '...' : '↻ Restart' }}
              </button>
              <button
                @click="viewLogs(service.container)"
                :disabled="service.status === 'not found'"
                class="px-3 py-1.5 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded text-xs text-white transition-colors"
              >
                Logs
              </button>
            </div>
          </div>
        </div>

        <!-- Quick Links -->
        <div class="mt-4 pt-4 border-t border-gray-700/50 flex flex-wrap gap-3">
          <a href="http://localhost:11030" target="_blank" class="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1">
            🌐 Web UI
          </a>
          <a href="http://localhost:11080/docs" target="_blank" class="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1">
            📡 API Docs
          </a>
          <a href="http://localhost:11085/mcp" target="_blank" class="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1">
            🔌 MCP Server
          </a>
        </div>
      </section>

      <!-- Managed Services -->
      <section class="bg-gray-800 rounded-xl p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span>⚙️</span> Managed Services
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="service in services"
            :key="service.name"
            class="bg-gray-700/50 rounded-lg p-4"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="text-white font-medium">{{ service.name }}</div>
              <span
                :class="['px-2 py-0.5 rounded text-xs font-medium', getStatusBg(service.status), getStatusColor(service.status)]"
              >
                {{ service.status }}
              </span>
            </div>
            <div class="text-gray-400 text-sm mb-3">{{ service.description }}</div>
            <div class="flex gap-2">
              <button
                @click="restartService(service.name)"
                :disabled="actionLoading[`service-${service.name}`] || service.status === 'not found'"
                class="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-xs text-white transition-colors"
              >
                {{ actionLoading[`service-${service.name}`] ? '...' : '↻ Restart' }}
              </button>
              <button
                @click="viewLogs(service.container)"
                :disabled="service.status === 'not found'"
                class="px-3 py-1.5 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded text-xs text-white transition-colors"
              >
                Logs
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- All Containers -->
      <section class="bg-gray-800 rounded-xl p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span>📦</span> All Containers
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-400 border-b border-gray-700">
                <th class="pb-3 pr-4">Name</th>
                <th class="pb-3 pr-4">Status</th>
                <th class="pb-3 pr-4">Image</th>
                <th class="pb-3 pr-4">Service</th>
                <th class="pb-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="container in containers"
                :key="container.id"
                class="border-b border-gray-700/50 hover:bg-gray-700/30"
              >
                <td class="py-3 pr-4">
                  <div class="text-white font-mono text-xs">{{ container.name }}</div>
                  <div class="text-gray-500 text-xs">{{ container.id }}</div>
                </td>
                <td class="py-3 pr-4">
                  <span
                    :class="['px-2 py-0.5 rounded text-xs font-medium', getStatusBg(container.status), getStatusColor(container.status)]"
                  >
                    {{ container.status }}
                  </span>
                </td>
                <td class="py-3 pr-4">
                  <div class="text-gray-300 text-xs truncate max-w-xs" :title="container.image">
                    {{ container.image }}
                  </div>
                </td>
                <td class="py-3 pr-4">
                  <span v-if="container.service" class="text-blue-400 text-xs">{{ container.service }}</span>
                  <span v-else class="text-gray-500 text-xs">-</span>
                </td>
                <td class="py-3">
                  <div class="flex gap-1">
                    <button
                      v-if="container.status !== 'running'"
                      @click="performAction(container.name, 'start')"
                      :disabled="actionLoading[`${container.name}-start`]"
                      class="px-2 py-1 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 rounded text-xs text-white transition-colors"
                    >
                      {{ actionLoading[`${container.name}-start`] ? '...' : 'Start' }}
                    </button>
                    <button
                      v-if="container.status === 'running'"
                      @click="performAction(container.name, 'stop')"
                      :disabled="actionLoading[`${container.name}-stop`]"
                      class="px-2 py-1 bg-red-600 hover:bg-red-500 disabled:bg-gray-600 rounded text-xs text-white transition-colors"
                    >
                      {{ actionLoading[`${container.name}-stop`] ? '...' : 'Stop' }}
                    </button>
                    <button
                      @click="performAction(container.name, 'restart')"
                      :disabled="actionLoading[`${container.name}-restart`]"
                      class="px-2 py-1 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 rounded text-xs text-white transition-colors"
                    >
                      {{ actionLoading[`${container.name}-restart`] ? '...' : '↻' }}
                    </button>
                    <button
                      @click="viewLogs(container.name)"
                      class="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs text-white transition-colors"
                    >
                      Logs
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <!-- Logs Modal -->
    <div
      v-if="logs.visible"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="closeLogs"
    >
      <div class="bg-gray-800 rounded-xl w-full max-w-4xl max-h-[80vh] flex flex-col">
        <div class="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 class="text-white font-medium">Logs: {{ logs.container }}</h3>
          <button @click="closeLogs" class="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        <pre class="flex-1 overflow-auto p-4 text-xs text-gray-300 font-mono whitespace-pre-wrap">{{ logs.content }}</pre>
      </div>
    </div>
  </div>
</template>
