import { ref, computed } from 'vue'
import { useConfig } from '../config.js'
import { imageModels } from '../constants/mobileConstants.js'

const { comfyuiUrl: COMFYUI_URL } = useConfig()

export function useImageGeneration() {
  const selectedImageModel = ref(imageModels[0].id)
  const imagePrompt = ref('')
  const imageGenerating = ref(false)
  const imageProgress = ref(0)
  const generatedImages = ref([])
  const imageError = ref('')

  const currentImageModel = computed(() => imageModels.find(m => m.id === selectedImageModel.value))

  function buildImageWorkflow() {
    const seed = Math.floor(Math.random() * 2147483647)
    const model = currentImageModel.value
    const negativePrompt = "blurry, low quality, distorted, ugly, deformed"

    if (model.type === 'flux') {
      return {
        prompt: {
          "1": { class_type: "UNETLoader", inputs: { unet_name: model.id, weight_dtype: "default" }},
          "2": { class_type: "DualCLIPLoader", inputs: { clip_name1: "t5xxl_fp16.safetensors", clip_name2: "clip_l.safetensors", type: "flux" }},
          "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: imagePrompt.value }},
          "4": { class_type: "EmptyLatentImage", inputs: { width: 1024, height: 1024, batch_size: 1 }},
          "5": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["3", 0] }},
          "6": { class_type: "RandomNoise", inputs: { noise_seed: seed }},
          "7": { class_type: "BasicScheduler", inputs: { model: ["1", 0], scheduler: "simple", steps: 20, denoise: 1.0 }},
          "8": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
          "9": { class_type: "SamplerCustomAdvanced", inputs: { noise: ["6", 0], guider: ["5", 0], sampler: ["8", 0], sigmas: ["7", 0], latent_image: ["4", 0] }},
          "10": { class_type: "VAELoader", inputs: { vae_name: "ae.safetensors" }},
          "11": { class_type: "VAEDecode", inputs: { vae: ["10", 0], samples: ["9", 0] }},
          "12": { class_type: "SaveImage", inputs: { images: ["11", 0], filename_prefix: "mobile_flux" }}
        }
      }
    } else {
      const size = model.type === 'sd15' ? 512 : 1024
      return {
        prompt: {
          "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
          "2": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: imagePrompt.value }},
          "3": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: negativePrompt }},
          "4": { class_type: "EmptyLatentImage", inputs: { width: size, height: size, batch_size: 1 }},
          "5": { class_type: "KSampler", inputs: {
            model: ["1", 0], positive: ["2", 0], negative: ["3", 0], latent_image: ["4", 0],
            seed, steps: 25, cfg: 7.0, sampler_name: "euler_ancestral", scheduler: "normal", denoise: 1.0
          }},
          "6": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["5", 0] }},
          "7": { class_type: "SaveImage", inputs: { images: ["6", 0], filename_prefix: "mobile_img" }}
        }
      }
    }
  }

  async function pollImageCompletion(promptId) {
    const maxAttempts = 180
    let attempts = 0

    while (attempts < maxAttempts) {
      try {
        const queueRes = await fetch(`${COMFYUI_URL}/queue`)
        const queue = await queueRes.json()
        if (queue.queue_running?.length > 0) {
          imageProgress.value = Math.min(90, imageProgress.value + 2)
        }

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
                  prompt: imagePrompt.value,
                  model: currentImageModel.value.name
                })
              }
            }
          }
          imageProgress.value = 100
          return
        }
      } catch (e) { /* retry */ }

      await new Promise(r => setTimeout(r, 1000))
      attempts++
    }
    throw new Error('Timeout')
  }

  async function generateImage() {
    if (!imagePrompt.value.trim()) {
      imageError.value = 'Enter a prompt'
      return
    }

    imageError.value = ''
    imageGenerating.value = true
    imageProgress.value = 0

    const workflow = buildImageWorkflow()

    try {
      const response = await fetch(`${COMFYUI_URL}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow)
      })

      if (!response.ok) throw new Error('Failed to submit')

      const data = await response.json()
      await pollImageCompletion(data.prompt_id)
    } catch (e) {
      imageError.value = e.message
    } finally {
      imageGenerating.value = false
    }
  }

  return {
    // State
    selectedImageModel,
    imagePrompt,
    imageGenerating,
    imageProgress,
    generatedImages,
    imageError,
    currentImageModel,
    // Methods
    generateImage
  }
}
