<script setup>
import { ref, computed } from 'vue'
import { useConfig } from '../config.js'

const { comfyuiUrl: COMFYUI_URL } = useConfig()

const models = [
  { id: 'pony-diffusion-v6-xl.safetensors', name: 'Pony Diffusion V6 XL', type: 'sdxl' },
  { id: 'noobai-xl-v1.1.safetensors', name: 'NoobAI XL v1.1', type: 'sdxl' },
  { id: 'illustrious-xl-v1.1.safetensors', name: 'Illustrious XL v1.1', type: 'sdxl' },
  { id: 'flux1-dev-abliterated-v2.safetensors', name: 'Flux Abliterated v2', type: 'flux' },
  { id: 'v1-5-pruned-emaonly.safetensors', name: 'Stable Diffusion 1.5', type: 'sd15' },
]

const selectedModel = ref(models[0].id)
const prompt = ref('')
const negativePrompt = ref('blurry, low quality, distorted, ugly, deformed')
const width = ref(1024)
const height = ref(1024)
const steps = ref(25)
const seed = ref(-1)
const generating = ref(false)
const progress = ref(0)
const generatedImages = ref([])
const error = ref('')

const currentModel = computed(() => models.find(m => m.id === selectedModel.value))

function randomSeed() {
  seed.value = Math.floor(Math.random() * 2147483647)
}

function buildWorkflow() {
  const model = currentModel.value
  const actualSeed = seed.value === -1 ? Math.floor(Math.random() * 2147483647) : seed.value

  if (model.type === 'flux') {
    return {
      prompt: {
        "1": { class_type: "UNETLoader", inputs: { unet_name: model.id, weight_dtype: "default" }},
        "2": { class_type: "CLIPLoader", inputs: { clip_name: "t5xxl_fp16.safetensors", type: "flux2" }},
        "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: prompt.value }},
        "4": { class_type: "EmptyFlux2LatentImage", inputs: { width: width.value, height: height.value, batch_size: 1 }},
        "5": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["3", 0] }},
        "6": { class_type: "RandomNoise", inputs: { noise_seed: actualSeed }},
        "7": { class_type: "BasicScheduler", inputs: { model: ["1", 0], scheduler: "simple", steps: steps.value, denoise: 1.0 }},
        "8": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
        "9": { class_type: "SamplerCustomAdvanced", inputs: { noise: ["6", 0], guider: ["5", 0], sampler: ["8", 0], sigmas: ["7", 0], latent_image: ["4", 0] }},
        "10": { class_type: "VAELoader", inputs: { vae_name: "ae.safetensors" }},
        "11": { class_type: "VAEDecode", inputs: { vae: ["10", 0], samples: ["9", 0] }},
        "12": { class_type: "SaveImage", inputs: { images: ["11", 0], filename_prefix: "webui_flux" }}
      }
    }
  } else {
    // SDXL and SD1.5
    const w = model.type === 'sd15' ? Math.min(width.value, 512) : width.value
    const h = model.type === 'sd15' ? Math.min(height.value, 512) : height.value

    return {
      prompt: {
        "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
        "2": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: prompt.value }},
        "3": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: negativePrompt.value }},
        "4": { class_type: "EmptyLatentImage", inputs: { width: w, height: h, batch_size: 1 }},
        "5": { class_type: "KSampler", inputs: {
          model: ["1", 0], positive: ["2", 0], negative: ["3", 0], latent_image: ["4", 0],
          seed: actualSeed, steps: steps.value, cfg: 7.0, sampler_name: "euler_ancestral", scheduler: "normal", denoise: 1.0
        }},
        "6": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["5", 0] }},
        "7": { class_type: "SaveImage", inputs: { images: ["6", 0], filename_prefix: "webui_img" }}
      }
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

    // Poll for completion
    await pollForCompletion(promptId)

  } catch (e) {
    error.value = e.message
  } finally {
    generating.value = false
  }
}

async function pollForCompletion(promptId) {
  const maxAttempts = 300 // 5 minutes max
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      // Check queue
      const queueRes = await fetch(`${COMFYUI_URL}/queue`)
      const queue = await queueRes.json()
      const running = queue.queue_running?.length || 0
      const pending = queue.queue_pending?.length || 0

      if (running > 0) {
        progress.value = Math.min(90, progress.value + 2)
      }

      // Check history
      const histRes = await fetch(`${COMFYUI_URL}/history/${promptId}`)
      const history = await histRes.json()

      if (history[promptId]) {
        const outputs = history[promptId].outputs || {}
        for (const nodeId in outputs) {
          if (outputs[nodeId].images) {
            for (const img of outputs[nodeId].images) {
              const imageUrl = `${COMFYUI_URL}/view?filename=${img.filename}&subfolder=${img.subfolder || ''}&type=${img.type || 'output'}`
              generatedImages.value.unshift({
                url: imageUrl,
                filename: img.filename,
                prompt: prompt.value,
                model: currentModel.value.name,
                timestamp: new Date().toLocaleTimeString()
              })
            }
          }
        }
        progress.value = 100
        return
      }

      if (running === 0 && pending === 0 && attempts > 5) {
        // Nothing running and our job isn't in history - might have failed
        throw new Error('Generation may have failed - check ComfyUI logs')
      }

    } catch (e) {
      if (e.message.includes('Generation may have failed')) throw e
      // Network errors - keep trying
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
        <h2 class="text-lg font-semibold">Settings</h2>

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
            placeholder="Describe your image..."
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 resize-none"
          ></textarea>
        </div>

        <!-- Negative Prompt -->
        <div v-if="currentModel?.type !== 'flux'">
          <label class="block text-sm text-gray-400 mb-1">Negative Prompt</label>
          <textarea
            v-model="negativePrompt"
            rows="2"
            placeholder="What to avoid..."
            class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 resize-none"
          ></textarea>
        </div>

        <!-- Size -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">Width</label>
            <input
              v-model.number="width"
              type="number"
              step="64"
              min="256"
              max="2048"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Height</label>
            <input
              v-model.number="height"
              type="number"
              step="64"
              min="256"
              max="2048"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        <!-- Steps & Seed -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">Steps</label>
            <input
              v-model.number="steps"
              type="number"
              min="1"
              max="100"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
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
        </div>

        <!-- Generate Button -->
        <button
          @click="generate"
          :disabled="generating"
          class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium transition-colors"
        >
          <span v-if="generating">
            Generating... {{ progress }}%
          </span>
          <span v-else>Generate Image</span>
        </button>

        <!-- Progress Bar -->
        <div v-if="generating" class="w-full bg-gray-700 rounded-full h-2">
          <div
            class="bg-blue-500 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>

        <!-- Error -->
        <div v-if="error" class="text-red-400 text-sm">{{ error }}</div>
      </div>
    </div>

    <!-- Generated Images -->
    <div class="space-y-4">
      <h2 class="text-lg font-semibold">Generated Images</h2>

      <div v-if="generatedImages.length === 0" class="bg-gray-800 rounded-lg p-8 text-center text-gray-500">
        No images generated yet
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="(img, idx) in generatedImages"
          :key="idx"
          class="bg-gray-800 rounded-lg overflow-hidden"
        >
          <img
            :src="img.url"
            :alt="img.prompt"
            class="w-full"
          />
          <div class="p-3 text-sm">
            <div class="text-gray-400">{{ img.model }} · {{ img.timestamp }}</div>
            <div class="text-gray-300 truncate">{{ img.prompt }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
