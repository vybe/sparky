<script setup>
import { ref, computed } from 'vue'
import { useConfig } from '../config.js'

const { comfyuiUrl: COMFYUI_URL } = useConfig()

const models = [
  { id: 'ltxv-2b-0.9.8-distilled.safetensors', name: 'LTX Video 2B (Fast)', steps: 20 },
  { id: 'ltxv-13b-0.9.8-distilled.safetensors', name: 'LTX Video 13B (Quality)', steps: 8 },
]

const resolutions = [
  { w: 512, h: 320, name: '512×320 (Fast)' },
  { w: 768, h: 512, name: '768×512 (Balanced)' },
  { w: 1024, h: 576, name: '1024×576 (HD)' },
]

const durations = [
  { frames: 25, name: '~1 second (25 frames)' },
  { frames: 49, name: '~2 seconds (49 frames)' },
  { frames: 97, name: '~4 seconds (97 frames)' },
  { frames: 145, name: '~6 seconds (145 frames)' },
  { frames: 241, name: '~10 seconds (241 frames)' },
]

const selectedModel = ref(models[0].id)
const selectedResolution = ref(resolutions[1])
const selectedDuration = ref(durations[1])
const prompt = ref('')
const negativePrompt = ref('blurry, low quality, distorted, watermark, ugly, deformed, static, frozen')
const seed = ref(-1)
const generating = ref(false)
const progress = ref(0)
const generatedVideos = ref([])
const error = ref('')

const currentModel = computed(() => models.find(m => m.id === selectedModel.value))

function randomSeed() {
  seed.value = Math.floor(Math.random() * 2147483647)
}

function buildWorkflow() {
  const model = currentModel.value
  const actualSeed = seed.value === -1 ? Math.floor(Math.random() * 2147483647) : seed.value
  const res = selectedResolution.value
  const frames = selectedDuration.value.frames

  return {
    prompt: {
      "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
      "2": { class_type: "CLIPLoader", inputs: { clip_name: "t5xxl_fp16.safetensors", type: "ltxv" }},
      "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: prompt.value + ", cinematic quality, high detail, smooth motion" }},
      "4": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: negativePrompt.value }},
      "5": { class_type: "LTXVConditioning", inputs: { positive: ["3", 0], negative: ["4", 0], frame_rate: 24.0 }},
      "6": { class_type: "EmptyLTXVLatentVideo", inputs: { width: res.w, height: res.h, length: frames, batch_size: 1 }},
      "7": { class_type: "LTXVScheduler", inputs: { steps: model.steps, max_shift: 2.05, base_shift: 0.95, stretch: true, terminal: 0.1, latent: ["6", 0] }},
      "8": { class_type: "RandomNoise", inputs: { noise_seed: actualSeed }},
      "9": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["5", 0] }},
      "10": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
      "11": { class_type: "SamplerCustomAdvanced", inputs: { noise: ["8", 0], guider: ["9", 0], sampler: ["10", 0], sigmas: ["7", 0], latent_image: ["6", 0] }},
      "12": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["11", 0] }},
      "13": { class_type: "VHS_VideoCombine", inputs: { images: ["12", 0], frame_rate: 24, loop_count: 0, filename_prefix: "webui_video", format: "video/h264-mp4", pingpong: false, save_output: true }}
    }
  }
}

async function generate() {
  if (!prompt.value.trim()) {
    error.value = 'Please enter a prompt'
    return
  }

  error.value = ''
  generating.value = true
  progress.value = 0

  try {
    const workflow = buildWorkflow()
    const response = await fetch(`${COMFYUI_URL}/prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(workflow)
    })

    if (!response.ok) throw new Error('Failed to submit prompt')

    const data = await response.json()
    const promptId = data.prompt_id

    await pollForCompletion(promptId)

  } catch (e) {
    error.value = e.message
  } finally {
    generating.value = false
  }
}

async function pollForCompletion(promptId) {
  const maxAttempts = 600 // 10 minutes max for video
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      const queueRes = await fetch(`${COMFYUI_URL}/queue`)
      const queue = await queueRes.json()
      const running = queue.queue_running?.length || 0

      if (running > 0) {
        progress.value = Math.min(95, progress.value + 0.5)
      }

      const histRes = await fetch(`${COMFYUI_URL}/history/${promptId}`)
      const history = await histRes.json()

      if (history[promptId]) {
        const outputs = history[promptId].outputs || {}
        for (const nodeId in outputs) {
          if (outputs[nodeId].gifs) {
            for (const vid of outputs[nodeId].gifs) {
              const videoUrl = `${COMFYUI_URL}/view?filename=${vid.filename}&subfolder=${vid.subfolder || ''}&type=${vid.type || 'output'}`
              generatedVideos.value.unshift({
                url: videoUrl,
                filename: vid.filename,
                prompt: prompt.value,
                model: currentModel.value.name,
                resolution: `${selectedResolution.value.w}×${selectedResolution.value.h}`,
                duration: selectedDuration.value.name,
                timestamp: new Date().toLocaleTimeString()
              })
            }
          }
        }
        progress.value = 100
        return
      }

    } catch (e) {
      // Keep trying
    }

    await new Promise(r => setTimeout(r, 1000))
    attempts++
  }

  throw new Error('Generation timed out')
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Controls -->
    <div class="space-y-4">
      <div class="bg-gray-800 rounded-lg p-4 space-y-4">
        <h2 class="text-lg font-semibold">Video Settings</h2>

        <!-- Model Selection -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Model</label>
          <select
            v-model="selectedModel"
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option v-for="model in models" :key="model.id" :value="model.id">
              {{ model.name }}
            </option>
          </select>
        </div>

        <!-- Prompt -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Prompt</label>
          <textarea
            v-model="prompt"
            rows="4"
            placeholder="Describe your video scene..."
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 resize-none"
          ></textarea>
        </div>

        <!-- Negative Prompt -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Negative Prompt</label>
          <textarea
            v-model="negativePrompt"
            rows="2"
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 resize-none"
          ></textarea>
        </div>

        <!-- Resolution -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Resolution</label>
          <select
            v-model="selectedResolution"
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option v-for="res in resolutions" :key="res.name" :value="res">
              {{ res.name }}
            </option>
          </select>
        </div>

        <!-- Duration -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Duration</label>
          <select
            v-model="selectedDuration"
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option v-for="dur in durations" :key="dur.frames" :value="dur">
              {{ dur.name }}
            </option>
          </select>
        </div>

        <!-- Seed -->
        <div>
          <label class="block text-sm text-gray-400 mb-1">Seed (-1 = random)</label>
          <div class="flex gap-2">
            <input
              v-model.number="seed"
              type="number"
              class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
            <button
              @click="randomSeed"
              class="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
            >🎲</button>
          </div>
        </div>

        <!-- Generate Button -->
        <button
          @click="generate"
          :disabled="generating"
          class="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium transition-colors"
        >
          <span v-if="generating">
            Generating... {{ Math.round(progress) }}%
          </span>
          <span v-else>Generate Video</span>
        </button>

        <!-- Progress Bar -->
        <div v-if="generating" class="w-full bg-gray-700 rounded-full h-2">
          <div
            class="bg-purple-500 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>

        <!-- Estimated Time -->
        <div v-if="generating" class="text-sm text-gray-400 text-center">
          Video generation can take 1-10 minutes depending on settings
        </div>

        <!-- Error -->
        <div v-if="error" class="text-red-400 text-sm">{{ error }}</div>
      </div>
    </div>

    <!-- Generated Videos -->
    <div class="space-y-4">
      <h2 class="text-lg font-semibold">Generated Videos</h2>

      <div v-if="generatedVideos.length === 0" class="bg-gray-800 rounded-lg p-8 text-center text-gray-500">
        No videos generated yet
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="(vid, idx) in generatedVideos"
          :key="idx"
          class="bg-gray-800 rounded-lg overflow-hidden"
        >
          <video
            :src="vid.url"
            controls
            loop
            class="w-full"
          ></video>
          <div class="p-3 text-sm space-y-1">
            <div class="text-gray-400">{{ vid.model }} · {{ vid.resolution }} · {{ vid.timestamp }}</div>
            <div class="text-gray-300 truncate">{{ vid.prompt }}</div>
            <a
              :href="vid.url"
              download
              class="inline-block text-blue-400 hover:text-blue-300 text-xs"
            >
              Download MP4
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
