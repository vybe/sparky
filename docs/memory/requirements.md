# Requirements

> **SINGLE SOURCE OF TRUTH** for all features in DGX Spark Web UI.

---

## Implemented Features

### 1. Dashboard Overview
**Status**: ✅ Complete
**Priority**: High
- [x] Hardware specifications display (GPU, CPU, Memory, Storage)
- [x] Network connection status (Local/VPN IPs)
- [x] Available models list (LLM, Video, Image, Audio)
- [x] Service links (Ollama, ComfyUI, Ultravox, etc.)

### 2. Chat Interface
**Status**: ✅ Complete
**Priority**: High
- [x] Model selection dropdown (Ollama models)
- [x] Streaming chat responses
- [x] Message history preservation
- [x] Copy response to clipboard
- [x] Clear conversation

### 3. Image Generation
**Status**: ✅ Complete
**Priority**: High
- [x] Prompt input with negative prompt
- [x] Model selection (Pony, NoobAI, Illustrious, Flux)
- [x] Resolution presets (512x512 to 1536x1024)
- [x] Step count and CFG scale controls
- [x] Seed input for reproducibility
- [x] Image preview and download
- [x] ComfyUI workflow submission

### 4. Video Generation
**Status**: ✅ Complete
**Priority**: High
- [x] Text-to-video prompt
- [x] Model selection (LTX Video 2B/13B)
- [x] Frame count selection (25-241 frames)
- [x] Resolution presets
- [x] Video preview and download
- [x] ComfyUI workflow submission

### 5. Voice Chat
**Status**: ✅ Complete
**Priority**: Medium
- [x] Audio recording (hold-to-record)
- [x] Ultravox speech-to-LLM processing
- [x] Chatterbox TTS response playback
- [x] Voice selection (28 predefined voices)
- [x] Conversation history display

### 6. Agent Chat (Claude Code)
**Status**: ✅ Complete
**Priority**: Medium
- [x] Claude Code integration on DGX
- [x] Session persistence
- [x] Session save/load/resume
- [x] Streaming responses
- [x] Tool restriction options
- [x] Sessions sorted by last usage
- [x] File upload (images, PDFs) via drag & drop or picker

### 7. Rick Agent (Family Assistant)
**Status**: ✅ Complete
**Priority**: Medium
- [x] Claude Code integration with agent-rick context
- [x] Session persistence (separate from Sparky)
- [x] Session save/load/resume
- [x] Streaming responses
- [x] Sessions sorted by last usage
- [x] File upload (images, PDFs) via drag & drop or picker

### 8. Research Agent (Goose)
**Status**: ✅ Complete
**Priority**: Medium
- [x] Goose CLI integration
- [x] Chat mode (quick Q&A)
- [x] Research mode (web search + file storage)
- [x] Saved research file listing
- [x] Research content viewing

### 9. Container Management
**Status**: ✅ Complete
**Priority**: High
- [x] Container list with status
- [x] Start/Stop/Restart actions
- [x] Container logs viewing
- [x] Service health status
- [x] Docker info display

### 10. Telemetry/Activity Monitor
**Status**: ✅ Complete
**Priority**: Medium
- [x] GPU utilization display
- [x] Memory usage bar
- [x] CPU usage
- [x] Disk space
- [x] Real-time polling (1s interval)

### 11. Mobile PWA
**Status**: ✅ Complete
**Priority**: Medium
- [x] Mobile-optimized layout
- [x] PWA manifest and service worker
- [x] iOS home screen app support
- [x] Touch-friendly controls
- [x] All desktop features accessible

---

## Planned Features

### WebSocket Support
**Status**: ⏳ Pending
**Priority**: Low
- [ ] Replace polling with WebSocket connections
- [ ] Real-time container status updates
- [ ] Live telemetry streaming

### Authentication
**Status**: ⏳ Pending
**Priority**: Low
- [ ] Optional API key authentication
- [ ] Session tokens
- [ ] Rate limiting

---

## Non-Functional Requirements

### Performance
- Chat streaming latency < 500ms
- Image generation UI responsive during generation
- Telemetry polling doesn't block UI

### Security
- No hardcoded credentials in committed code
- Sensitive config via environment variables
- Docker socket access documented

### Compatibility
- Chrome 90+, Firefox 85+, Safari 14+
- iOS Safari (PWA support)
- Responsive 320px to 2560px
