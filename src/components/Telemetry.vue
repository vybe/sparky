<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useConfig } from '../config.js'

const { comfyuiUrl: COMFYUI_URL, telemetryUrl: TELEMETRY_URL, ollamaUrl: OLLAMA_URL } = useConfig()

const gpuStats = ref(null)
const systemStats = ref(null)
const ollamaStats = ref(null)
const loading = ref(true)
const error = ref('')
const lastUpdate = ref(null)

let pollInterval = null

async function fetchStats() {
  try {
    // Fetch GPU stats from ComfyUI
    const comfyRes = await fetch(`${COMFYUI_URL}/system_stats`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (comfyRes?.ok) {
      const data = await comfyRes.json()
      gpuStats.value = {
        name: data.devices?.[0]?.name || 'NVIDIA GB10',
        vramUsed: (data.devices?.[0]?.vram_total - data.devices?.[0]?.vram_free) / (1024 ** 3),
        vramTotal: data.devices?.[0]?.vram_total / (1024 ** 3),
        vramPercent: ((data.devices?.[0]?.vram_total - data.devices?.[0]?.vram_free) / data.devices?.[0]?.vram_total * 100),
        comfyVersion: data.system?.comfyui_version
      }
    }

    // Fetch system stats from telemetry API
    const sysRes = await fetch(`${TELEMETRY_URL}/stats`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (sysRes?.ok) {
      systemStats.value = await sysRes.json()
    }

    // Fetch Ollama stats
    const ollamaRes = await fetch(`${OLLAMA_URL}/api/ps`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (ollamaRes?.ok) {
      const data = await ollamaRes.json()
      ollamaStats.value = {
        models: data.models || [],
        count: data.models?.length || 0
      }
    }

    lastUpdate.value = new Date()
    loading.value = false
    error.value = ''
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

function formatBytes(gb) {
  return gb?.toFixed(1) || '0'
}

function formatPercent(pct) {
  return pct?.toFixed(0) || '0'
}

onMounted(() => {
  fetchStats()
  pollInterval = setInterval(fetchStats, 5000) // Poll every 5 seconds
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="bg-gray-800/80 rounded-lg p-3 text-xs">
    <div class="flex items-center justify-between mb-2">
      <span class="text-gray-400 font-medium">DGX Telemetry</span>
      <span v-if="lastUpdate" class="text-gray-500">
        {{ lastUpdate.toLocaleTimeString() }}
      </span>
    </div>

    <div v-if="loading" class="text-gray-500">Loading...</div>

    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <!-- GPU Stats -->
      <div class="space-y-1">
        <div class="text-gray-400">GPU</div>
        <div v-if="systemStats?.gpu" class="space-y-1">
          <div class="flex items-baseline gap-1">
            <span class="text-lg font-bold" :class="systemStats.gpu.temp > 70 ? 'text-red-400' : 'text-green-400'">{{ systemStats.gpu.temp }}°C</span>
            <span class="text-gray-500">{{ systemStats.gpu.power }}W</span>
          </div>
          <div class="text-gray-500 text-xs">{{ systemStats.gpu.name }}</div>
        </div>
        <div v-else-if="gpuStats" class="text-gray-500">
          {{ gpuStats.name || 'GPU' }}
        </div>
        <div v-else class="text-gray-500">N/A</div>
      </div>

      <!-- CPU -->
      <div class="space-y-1">
        <div class="text-gray-400">CPU</div>
        <div v-if="systemStats?.cpu" class="space-y-1">
          <div class="flex items-baseline gap-1">
            <span class="text-lg font-bold text-blue-400">{{ formatPercent(systemStats.cpu.percent) }}</span>
            <span class="text-gray-500">%</span>
          </div>
          <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              class="h-full bg-blue-500 transition-all"
              :style="{ width: `${systemStats.cpu.percent}%` }"
            ></div>
          </div>
        </div>
        <div v-else class="text-gray-500">N/A</div>
      </div>

      <!-- Unified Memory (shared CPU/GPU) -->
      <div class="space-y-1">
        <div class="text-gray-400">Memory <span class="text-gray-600 text-xs">(unified)</span></div>
        <div v-if="systemStats?.memory" class="space-y-1">
          <div class="flex items-baseline gap-1">
            <span class="text-lg font-bold text-purple-400">{{ formatBytes(systemStats.memory.used) }}</span>
            <span class="text-gray-500">/ {{ formatBytes(systemStats.memory.total) }} GB</span>
          </div>
          <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              class="h-full bg-purple-500 transition-all"
              :style="{ width: `${systemStats.memory.percent}%` }"
            ></div>
          </div>
        </div>
        <div v-else class="text-gray-500">N/A</div>
      </div>

      <!-- GPU Temp / Ollama -->
      <div class="space-y-1">
        <div class="text-gray-400">Ollama Models</div>
        <div v-if="ollamaStats" class="space-y-1">
          <div class="flex items-baseline gap-1">
            <span class="text-lg font-bold text-yellow-400">{{ ollamaStats.count }}</span>
            <span class="text-gray-500">loaded</span>
          </div>
          <div v-if="ollamaStats.models.length" class="text-gray-500 truncate">
            {{ ollamaStats.models.map(m => m.name.split(':')[0]).join(', ') }}
          </div>
          <div v-else class="text-gray-500">None active</div>
        </div>
        <div v-else class="text-gray-500">N/A</div>
      </div>
    </div>

    <!-- Disk row -->
    <div v-if="systemStats?.disk" class="mt-3 pt-2 border-t border-gray-700 flex gap-4 text-xs text-gray-400">
      <span>Disk: <span class="text-white">{{ formatBytes(systemStats.disk.used) }} / {{ formatBytes(systemStats.disk.total) }} GB</span></span>
      <span class="text-gray-600">({{ formatPercent(systemStats.disk.percent) }}% used)</span>
    </div>
  </div>
</template>
