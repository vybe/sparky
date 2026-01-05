import { ref, computed } from 'vue'
import { useConfig } from '../config.js'
import { videoModels, videoPresets } from '../constants/mobileConstants.js'

const { comfyuiUrl: COMFYUI_URL } = useConfig()

export function useVideoGeneration() {
  const selectedVideoModel = ref(videoModels[0].id)
  const selectedVideoPreset = ref(videoPresets[0])
  const videoPrompt = ref('')
  const videoGenerating = ref(false)
  const videoProgress = ref(0)
  const generatedVideos = ref([])
  const videoError = ref('')

  const currentVideoModel = computed(() => videoModels.find(m => m.id === selectedVideoModel.value))

  async function pollVideoCompletion(promptId) {
    const maxAttempts = 300
    let attempts = 0

    while (attempts < maxAttempts) {
      try {
        const queueRes = await fetch(`${COMFYUI_URL}/queue`)
        const queue = await queueRes.json()
        if (queue.queue_running?.length > 0) {
          videoProgress.value = Math.min(90, videoProgress.value + 1)
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
                  prompt: videoPrompt.value,
                  model: currentVideoModel.value.name,
                  preset: selectedVideoPreset.value.name
                })
              }
            }
          }
          videoProgress.value = 100
          return
        }
      } catch (e) { /* retry */ }

      await new Promise(r => setTimeout(r, 1000))
      attempts++
    }
    throw new Error('Timeout')
  }

  async function generateVideo() {
    if (!videoPrompt.value.trim()) {
      videoError.value = 'Enter a prompt'
      return
    }

    videoError.value = ''
    videoGenerating.value = true
    videoProgress.value = 0

    const seed = Math.floor(Math.random() * 2147483647)
    const model = currentVideoModel.value
    const preset = selectedVideoPreset.value

    const workflow = {
      prompt: {
        "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
        "2": { class_type: "CLIPLoader", inputs: { clip_name: "t5xxl_fp16.safetensors", type: "ltxv" }},
        "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: videoPrompt.value + ", cinematic, smooth motion" }},
        "4": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: "blurry, low quality, static, frozen" }},
        "5": { class_type: "LTXVConditioning", inputs: { positive: ["3", 0], negative: ["4", 0], frame_rate: 24.0 }},
        "6": { class_type: "EmptyLTXVLatentVideo", inputs: { width: preset.w, height: preset.h, length: preset.frames, batch_size: 1 }},
        "7": { class_type: "LTXVScheduler", inputs: { steps: model.steps, max_shift: 2.05, base_shift: 0.95, stretch: true, terminal: 0.1, latent: ["6", 0] }},
        "8": { class_type: "RandomNoise", inputs: { noise_seed: seed }},
        "9": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["5", 0] }},
        "10": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
        "11": { class_type: "SamplerCustomAdvanced", inputs: { noise: ["8", 0], guider: ["9", 0], sampler: ["10", 0], sigmas: ["7", 0], latent_image: ["6", 0] }},
        "12": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["11", 0] }},
        "13": { class_type: "VHS_VideoCombine", inputs: { images: ["12", 0], frame_rate: 24, loop_count: 0, filename_prefix: "mobile_video", format: "video/h264-mp4", pingpong: false, save_output: true }}
      }
    }

    try {
      const response = await fetch(`${COMFYUI_URL}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow)
      })

      if (!response.ok) throw new Error('Failed to submit')

      const data = await response.json()
      await pollVideoCompletion(data.prompt_id)
    } catch (e) {
      videoError.value = e.message
    } finally {
      videoGenerating.value = false
    }
  }

  return {
    // State
    selectedVideoModel,
    selectedVideoPreset,
    videoPrompt,
    videoGenerating,
    videoProgress,
    generatedVideos,
    videoError,
    currentVideoModel,
    // Methods
    generateVideo
  }
}
