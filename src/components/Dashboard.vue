<script setup>
import { ref, onMounted } from 'vue'
import { useConfig } from '../config.js'

const { ollamaUrl: OLLAMA_URL } = useConfig()

// Network configuration
const network = {
  local: {
    name: 'Local Network',
    ip: import.meta.env.VITE_LOCAL_IP || '192.168.1.xxx',
    description: 'Direct connection when on same network'
  },
  tailscale: {
    name: 'Tailscale VPN',
    ip: import.meta.env.VITE_VPN_IP || '100.xxx.xxx.xxx',
    description: 'Remote access via VPN'
  }
}

// Services with port mappings
const services = [
  {
    name: 'Open WebUI',
    description: 'Chat interface for Ollama models',
    icon: '💬',
    localPort: 8080,
    tunnelPort: 11003,
    path: ''
  },
  {
    name: 'ComfyUI',
    description: 'Image & video generation workflows',
    icon: '🎨',
    localPort: 8188,
    tunnelPort: 11005,
    path: ''
  },
  {
    name: 'JupyterLab',
    description: 'Python notebooks & experiments',
    icon: '📓',
    localPort: 11002,
    tunnelPort: 11002,
    path: ''
  },
  {
    name: 'Trinity Web UI',
    description: 'Agent orchestration platform',
    icon: '🤖',
    localPort: 3000,
    tunnelPort: 11030,
    path: ''
  },
  {
    name: 'Trinity API',
    description: 'REST API documentation',
    icon: '📡',
    localPort: 8000,
    tunnelPort: 11080,
    path: '/docs'
  },
  {
    name: 'DGX Dashboard',
    description: 'System monitoring dashboard',
    icon: '📊',
    localPort: 11000,
    tunnelPort: 11000,
    path: ''
  }
]

// Hardware specs
const hardware = {
  gpu: {
    name: 'NVIDIA GB10',
    arch: 'Grace Blackwell',
    compute: '~100 TFLOPs FP16, 1 PFLOP FP4',
    cuda: '13.0'
  },
  cpu: {
    name: '20-core ARM',
    detail: '10x Cortex-X925 + 10x Cortex-A725'
  },
  memory: {
    size: '128 GB',
    type: 'Unified LPDDR5X',
    bandwidth: '273 GB/s'
  },
  storage: {
    size: '4 TB NVMe SSD',
    free: '~3.0 TB'
  }
}

// Available models summary
const models = {
  llm: [
    { name: 'gpt-oss:120b', size: '65GB', speed: '37 tok/s' },
    { name: 'deepseek-r1:70b', size: '42GB', speed: 'Fast' },
    { name: 'qwen3-vl:235b', size: '143GB', speed: 'Vision+LLM' },
    { name: 'llama4:scout', size: '67GB', speed: 'Very fast' },
    { name: 'ministral-3:14b', size: '9.1GB', speed: '27 tok/s' },
    { name: 'ministral-3-reasoning:14b', size: '8.2GB', speed: '27 tok/s' }
  ],
  video: [
    { name: 'LTX Video 2B', size: '6GB', speed: '~4-8s' },
    { name: 'LTX Video 13B', size: '27GB', speed: '~55-87s' }
  ],
  image: [
    { name: 'SD 1.5', size: '2GB', speed: '~3s' },
    { name: 'FLUX Schnell', size: '15GB', speed: '~10-15s' },
    { name: 'Pony Diffusion V6 XL', size: '6.5GB', speed: '~65s' },
    { name: 'Flux Abliterated v2', size: '23GB', speed: '~5min' }
  ],
  audio: [
    { name: 'Whisper large-v3', size: 'Docker', speed: '~1min/10s audio' },
    { name: 'Chatterbox TTS', size: 'Docker', speed: 'Real-time' },
    { name: 'Ultravox v0.3', size: '~16GB', speed: 'Real-time' }
  ]
}

const ollamaModels = ref([])
const loadingModels = ref(true)

function getUrl(service, type) {
  const ip = type === 'local' ? network.local.ip : network.tailscale.ip
  const port = service.localPort
  return `http://${ip}:${port}${service.path}`
}

async function fetchOllamaModels() {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`, { signal: AbortSignal.timeout(5000) })
    if (res.ok) {
      const data = await res.json()
      ollamaModels.value = data.models || []
    }
  } catch (e) {
    console.error('Failed to fetch Ollama models:', e)
  } finally {
    loadingModels.value = false
  }
}

onMounted(() => {
  fetchOllamaModels()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Instance Overview -->
    <section class="bg-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span>⚡</span> DGX Spark Instance
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- GPU -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-1">GPU</div>
          <div class="text-white font-medium">{{ hardware.gpu.name }}</div>
          <div class="text-gray-500 text-xs mt-1">{{ hardware.gpu.arch }}</div>
          <div class="text-green-400 text-xs mt-1">{{ hardware.gpu.compute }}</div>
        </div>

        <!-- CPU -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-1">CPU</div>
          <div class="text-white font-medium">{{ hardware.cpu.name }}</div>
          <div class="text-gray-500 text-xs mt-1">{{ hardware.cpu.detail }}</div>
        </div>

        <!-- Memory -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-1">Memory</div>
          <div class="text-white font-medium">{{ hardware.memory.size }}</div>
          <div class="text-gray-500 text-xs mt-1">{{ hardware.memory.type }}</div>
          <div class="text-blue-400 text-xs mt-1">{{ hardware.memory.bandwidth }}</div>
        </div>

        <!-- Storage -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-1">Storage</div>
          <div class="text-white font-medium">{{ hardware.storage.size }}</div>
          <div class="text-gray-500 text-xs mt-1">{{ hardware.storage.free }} free</div>
        </div>
      </div>

      <!-- Network Info -->
      <div class="mt-4 pt-4 border-t border-gray-700 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="flex items-center gap-3">
          <span class="text-blue-400">🏠</span>
          <div>
            <div class="text-gray-400 text-sm">{{ network.local.name }}</div>
            <div class="text-white font-mono text-sm">{{ network.local.ip }}</div>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-purple-400">🌐</span>
          <div>
            <div class="text-gray-400 text-sm">{{ network.tailscale.name }}</div>
            <div class="text-white font-mono text-sm">{{ network.tailscale.ip }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Services -->
    <section class="bg-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span>🔗</span> Services
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="service in services"
          :key="service.name"
          class="bg-gray-700/50 rounded-lg p-4"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xl">{{ service.icon }}</span>
            <div class="text-white font-medium">{{ service.name }}</div>
          </div>
          <div class="text-gray-400 text-sm mb-3">{{ service.description }}</div>
          <div class="flex gap-2">
            <a
              :href="getUrl(service, 'local')"
              target="_blank"
              class="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs text-white text-center transition-colors"
            >
              🏠 Local
            </a>
            <a
              :href="getUrl(service, 'tailscale')"
              target="_blank"
              class="flex-1 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 rounded text-xs text-white text-center transition-colors"
            >
              🌐 Tailscale
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Models Overview -->
    <section class="bg-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span>🧠</span> Available Models
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- LLMs -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-yellow-400 font-medium mb-2 flex items-center gap-2">
            <span>💬</span> LLMs (Ollama)
          </div>
          <div class="space-y-1.5">
            <div
              v-for="model in models.llm"
              :key="model.name"
              class="text-xs"
            >
              <div class="text-gray-300">{{ model.name }}</div>
              <div class="text-gray-500">{{ model.size }} · {{ model.speed }}</div>
            </div>
          </div>
        </div>

        <!-- Video -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-red-400 font-medium mb-2 flex items-center gap-2">
            <span>🎬</span> Video Gen
          </div>
          <div class="space-y-1.5">
            <div
              v-for="model in models.video"
              :key="model.name"
              class="text-xs"
            >
              <div class="text-gray-300">{{ model.name }}</div>
              <div class="text-gray-500">{{ model.size }} · {{ model.speed }}</div>
            </div>
          </div>
        </div>

        <!-- Image -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-green-400 font-medium mb-2 flex items-center gap-2">
            <span>🎨</span> Image Gen
          </div>
          <div class="space-y-1.5">
            <div
              v-for="model in models.image"
              :key="model.name"
              class="text-xs"
            >
              <div class="text-gray-300">{{ model.name }}</div>
              <div class="text-gray-500">{{ model.size }} · {{ model.speed }}</div>
            </div>
          </div>
        </div>

        <!-- Audio -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-blue-400 font-medium mb-2 flex items-center gap-2">
            <span>🎤</span> Audio
          </div>
          <div class="space-y-1.5">
            <div
              v-for="model in models.audio"
              :key="model.name"
              class="text-xs"
            >
              <div class="text-gray-300">{{ model.name }}</div>
              <div class="text-gray-500">{{ model.size }} · {{ model.speed }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Ollama Models -->
      <div v-if="!loadingModels && ollamaModels.length" class="mt-4 pt-4 border-t border-gray-700">
        <div class="text-gray-400 text-sm mb-2">Installed Ollama Models ({{ ollamaModels.length }})</div>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="model in ollamaModels"
            :key="model.name"
            class="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300"
          >
            {{ model.name }}<span v-if="model.details?.parameter_size" class="text-gray-500 ml-1">({{ model.details.parameter_size }})</span>
          </span>
        </div>
      </div>
    </section>

    <!-- Quick Reference -->
    <section class="bg-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span>📋</span> Quick Reference
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- SSH Access -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-2">SSH Access</div>
          <div class="font-mono text-xs text-gray-300 bg-gray-800 p-2 rounded overflow-x-auto">
            ssh {{ network.local.ip }}
          </div>
          <div class="font-mono text-xs text-gray-300 bg-gray-800 p-2 rounded mt-2 overflow-x-auto">
            ssh {{ network.tailscale.ip }}
          </div>
        </div>

        <!-- Performance Notes -->
        <div class="bg-gray-700/50 rounded-lg p-4">
          <div class="text-gray-400 text-sm mb-2">Performance Notes</div>
          <div class="text-xs text-gray-300 space-y-1">
            <div><span class="text-green-400">✓</span> Best for: LLM prefill, FP4/FP8 inference, training</div>
            <div><span class="text-yellow-400">~</span> Moderate: Video gen (use LTX 8-step distilled)</div>
            <div><span class="text-red-400">✗</span> Slower: Token generation, image diffusion (bandwidth-bound)</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
