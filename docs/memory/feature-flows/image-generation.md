# Feature: Image Generation

## Overview
Text-to-image generation using ComfyUI with SDXL, Flux, and SD 1.5 models.

## User Story
As a user, I want to generate images from text prompts so that I can create visual content using local AI models.

## Entry Points
- **UI**: `src/components/ImageGenerator.vue:167` - Controls and gallery layout
- **API**: ComfyUI API at `http://localhost:11005/prompt`

## Frontend Layer

### Components
- `src/components/ImageGenerator.vue:7-13` - Model list (Pony, NoobAI, Illustrious, Flux, SD1.5)
- `src/components/ImageGenerator.vue:174-184` - Model selector dropdown
- `src/components/ImageGenerator.vue:188-195` - Prompt textarea
- `src/components/ImageGenerator.vue:209-233` - Width/height/steps/seed controls
- `src/components/ImageGenerator.vue:264-273` - Generate button with progress
- `src/components/ImageGenerator.vue:296-312` - Generated images gallery

### Composables
- `src/composables/useImageGeneration.js:7-140` - Used by Mobile.vue
- `ImageGenerator.vue` uses inline state (not extracted to composable)

**Key State:**
```javascript
selectedModel    // ref(models[0].id) - Selected model filename
prompt           // ref('') - Positive prompt text
negativePrompt   // ref('blurry...') - Negative prompt
width, height    // ref(1024) - Image dimensions
steps            // ref(25) - Sampling steps
seed             // ref(-1) - Random seed (-1 = random)
generating       // ref(false) - Generation in progress
progress         // ref(0) - Progress percentage 0-100
generatedImages  // ref([]) - Generated image history
```

### API Calls

**Submit Workflow:**
```javascript
// src/components/ImageGenerator.vue:88-92
const response = await fetch(`${COMFYUI_URL}/prompt`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(workflow)
})
// Response: { prompt_id: "uuid" }
```

**Poll Queue:**
```javascript
// src/components/ImageGenerator.vue:116
const queueRes = await fetch(`${COMFYUI_URL}/queue`)
// Response: { queue_running: [...], queue_pending: [...] }
```

**Check History:**
```javascript
// src/components/ImageGenerator.vue:126
const histRes = await fetch(`${COMFYUI_URL}/history/${promptId}`)
// Response: { [promptId]: { outputs: { nodeId: { images: [...] } } } }
```

**Fetch Image:**
```javascript
// Constructed URL
`${COMFYUI_URL}/view?filename=${img.filename}&subfolder=${img.subfolder}&type=output`
```

## ComfyUI Workflow Structure

### SDXL/SD1.5 Models (Pony, NoobAI, Illustrious, SD1.5)
```javascript
// src/components/ImageGenerator.vue:59-73
{
  "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
  "2": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: prompt }},
  "3": { class_type: "CLIPTextEncode", inputs: { clip: ["1", 1], text: negativePrompt }},
  "4": { class_type: "EmptyLatentImage", inputs: { width, height, batch_size: 1 }},
  "5": { class_type: "KSampler", inputs: {
    model: ["1", 0], positive: ["2", 0], negative: ["3", 0], latent_image: ["4", 0],
    seed, steps, cfg: 7.0, sampler_name: "euler_ancestral", scheduler: "normal", denoise: 1.0
  }},
  "6": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["5", 0] }},
  "7": { class_type: "SaveImage", inputs: { images: ["6", 0], filename_prefix: "webui_img" }}
}
```

### Flux Model
```javascript
// src/components/ImageGenerator.vue:38-53
{
  "1": { class_type: "UNETLoader", inputs: { unet_name: model.id, weight_dtype: "default" }},
  "2": { class_type: "CLIPLoader", inputs: { clip_name: "t5xxl_fp16.safetensors", type: "flux2" }},
  "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: prompt }},
  "4": { class_type: "EmptyFlux2LatentImage", inputs: { width, height, batch_size: 1 }},
  "5": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["3", 0] }},
  "6": { class_type: "RandomNoise", inputs: { noise_seed: seed }},
  "7": { class_type: "BasicScheduler", inputs: { model: ["1", 0], scheduler: "simple", steps, denoise: 1.0 }},
  "8": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
  "9": { class_type: "SamplerCustomAdvanced", inputs: { ... }},
  "10": { class_type: "VAELoader", inputs: { vae_name: "ae.safetensors" }},
  "11": { class_type: "VAEDecode", inputs: { vae: ["10", 0], samples: ["9", 0] }},
  "12": { class_type: "SaveImage", inputs: { images: ["11", 0], filename_prefix: "webui_flux" }}
}
```

## Data Flow

1. **User enters prompt**: Text stored in `prompt` ref
2. **User clicks Generate**: `generate()` called
3. **Workflow built**: `buildWorkflow()` creates ComfyUI JSON based on model type
4. **Submit to ComfyUI**: POST to `/prompt` returns `prompt_id`
5. **Polling starts**: `pollForCompletion()` checks queue and history
6. **Progress updates**: Progress bar updated during polling
7. **Completion detected**: Image URLs extracted from history
8. **Gallery updated**: New image prepended to `generatedImages`

```
prompt --> buildWorkflow() --> POST /prompt --> prompt_id
                                                   |
                                         pollForCompletion()
                                                   |
                             GET /queue <-- poll -- GET /history/{id}
                                                   |
                                            extract images
                                                   |
                                     GET /view?filename=... --> display
```

## External Services

### ComfyUI API (port 8188 / tunnel 11005)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Submit workflow for execution |
| `/queue` | GET | Check running/pending jobs |
| `/history/{prompt_id}` | GET | Get job results |
| `/view` | GET | Fetch generated image file |
| `/system_stats` | GET | Check ComfyUI status |

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Empty prompt | Validation check | `error.value` message | Fix prompt |
| ComfyUI offline | Fetch fails | Error message | Check Manage tab |
| Generation timeout | 300 attempts | "Generation timed out" | Retry |
| Job failed | Queue empty, no history | "Generation may have failed" | Check logs |

## Configuration

- **COMFYUI_URL**: `src/config.js:5` defaults to `http://localhost:11005`
- **Models hardcoded**: `src/components/ImageGenerator.vue:7-13`

## Performance Notes

| Model | Type | Approx Time | Resolution |
|-------|------|-------------|------------|
| SD 1.5 | sd15 | ~3s | 512x512 |
| Pony/NoobAI/Illustrious | sdxl | ~65s | 1024x1024 |
| Flux Abliterated | flux | ~5min | 1024x1024 |

## Related Flows

- **Upstream**: Telemetry flow monitors GPU usage during generation
- **Downstream**: Video Generation uses similar ComfyUI patterns
