# Feature: Video Generation

## Overview
Text-to-video generation using ComfyUI with LTX Video models (2B and 13B).

## User Story
As a user, I want to generate videos from text prompts so that I can create animated content using local AI models.

## Entry Points
- **UI**: `src/components/VideoGenerator.vue:151` - Controls and video gallery
- **API**: ComfyUI API at `http://localhost:11005/prompt`

## Frontend Layer

### Components
- `src/components/VideoGenerator.vue:7-10` - LTX Video models (2B Fast, 13B Quality)
- `src/components/VideoGenerator.vue:12-16` - Resolution presets
- `src/components/VideoGenerator.vue:18-24` - Duration presets (frames)
- `src/components/VideoGenerator.vue:159-168` - Model selector
- `src/components/VideoGenerator.vue:171-179` - Prompt textarea
- `src/components/VideoGenerator.vue:192-215` - Resolution/duration selectors
- `src/components/VideoGenerator.vue:235-244` - Generate button with progress

### Composables
- `src/composables/useVideoGeneration.js:7-122` - Used by Mobile.vue

**Key State:**
```javascript
selectedModel      // ref(models[0].id) - LTX model filename
selectedResolution // ref({ w: 768, h: 512 }) - Video dimensions
selectedDuration   // ref({ frames: 49 }) - Frame count
prompt            // ref('') - Video description
negativePrompt    // ref('blurry...') - Negative prompt
seed              // ref(-1) - Random seed
generating        // ref(false) - Generation in progress
progress          // ref(0) - Progress percentage
generatedVideos   // ref([]) - Video history
```

### API Calls

**Submit Workflow:**
```javascript
// src/components/VideoGenerator.vue:80-84
const response = await fetch(`${COMFYUI_URL}/prompt`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(workflow)
})
```

**Poll for Completion:**
```javascript
// src/components/VideoGenerator.vue:106,114
const queueRes = await fetch(`${COMFYUI_URL}/queue`)
const histRes = await fetch(`${COMFYUI_URL}/history/${promptId}`)
```

## ComfyUI Workflow Structure

### LTX Video Workflow
```javascript
// src/components/VideoGenerator.vue:49-65
{
  "1": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: model.id }},
  "2": { class_type: "CLIPLoader", inputs: { clip_name: "t5xxl_fp16.safetensors", type: "ltxv" }},
  "3": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: prompt + ", cinematic quality" }},
  "4": { class_type: "CLIPTextEncode", inputs: { clip: ["2", 0], text: negativePrompt }},
  "5": { class_type: "LTXVConditioning", inputs: { positive: ["3", 0], negative: ["4", 0], frame_rate: 24.0 }},
  "6": { class_type: "EmptyLTXVLatentVideo", inputs: { width, height, length: frames, batch_size: 1 }},
  "7": { class_type: "LTXVScheduler", inputs: { steps: model.steps, max_shift: 2.05, base_shift: 0.95, stretch: true, terminal: 0.1, latent: ["6", 0] }},
  "8": { class_type: "RandomNoise", inputs: { noise_seed: seed }},
  "9": { class_type: "BasicGuider", inputs: { model: ["1", 0], conditioning: ["5", 0] }},
  "10": { class_type: "KSamplerSelect", inputs: { sampler_name: "euler" }},
  "11": { class_type: "SamplerCustomAdvanced", inputs: { noise, guider, sampler, sigmas, latent_image }},
  "12": { class_type: "VAEDecode", inputs: { vae: ["1", 2], samples: ["11", 0] }},
  "13": { class_type: "VHS_VideoCombine", inputs: { images: ["12", 0], frame_rate: 24, filename_prefix: "webui_video", format: "video/h264-mp4" }}
}
```

**Key Differences from Image:**
- Uses `EmptyLTXVLatentVideo` instead of `EmptyLatentImage`
- Uses `LTXVScheduler` instead of standard scheduler
- Uses `LTXVConditioning` to set frame rate
- Uses `VHS_VideoCombine` to encode video output
- Output is in `outputs[nodeId].gifs` (not `images`)

## Data Flow

1. **Configure generation**: User selects model, resolution, duration
2. **Enter prompt**: Description stored in `prompt` ref
3. **Click Generate**: `generate()` builds and submits workflow
4. **Long polling**: 600 attempts (10 min timeout) checks queue/history
5. **Video complete**: MP4 URL extracted from history `gifs` array
6. **Display**: Video element with controls and download link

```
Settings + Prompt --> buildWorkflow() --> POST /prompt
                                              |
                                         prompt_id
                                              |
                     pollForCompletion() <----+
                           |
            GET /history/{id} --> outputs.gifs[].filename
                                              |
                           GET /view?filename=... --> <video>
```

## External Services

### ComfyUI API (port 8188 / tunnel 11005)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Submit LTX Video workflow |
| `/queue` | GET | Check generation status |
| `/history/{id}` | GET | Get completed video info |
| `/view` | GET | Stream video file |

### Video Output Format
- **Container**: MP4 (H.264)
- **Frame Rate**: 24 FPS
- **Duration**: frames / 24 seconds

## Resolution and Duration Presets

| Resolution | Frames | Duration | Model | Est. Time |
|------------|--------|----------|-------|-----------|
| 512x320 | 25 | ~1s | 2B | 4-5s |
| 768x512 | 49 | ~2s | 2B | 8-9s |
| 1024x576 | 241 | ~10s | 13B | ~87s |

**Model Steps:**
- LTX 2B (distilled): 20 steps
- LTX 13B (distilled): 8 steps

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Empty prompt | Validation | Error message | Fix prompt |
| ComfyUI offline | Fetch fails | Error message | Check Manage |
| Timeout (10 min) | 600 attempts | "Generation timed out" | Retry with smaller size |
| OOM | No output | "Generation may have failed" | Reduce resolution/frames |

## Configuration

- **COMFYUI_URL**: `src/config.js:5` defaults to `http://localhost:11005`
- **Model files**: Hardcoded in component

## Performance Notes

| Model | Resolution | Frames | Time |
|-------|------------|--------|------|
| 2B | 512x320 | 25 | ~4s |
| 2B | 768x512 | 49 | ~9s |
| 13B | 768x512 | 145 | ~57s |
| 13B | 1024x576 | 241 | ~87s |

## Related Flows

- **Upstream**: Telemetry monitors GPU during generation
- **Parallel**: Image Generation uses same ComfyUI API patterns
