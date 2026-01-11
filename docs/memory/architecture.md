# Architecture

> Current system design for DGX Spark Web UI.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3 + Composition API |
| Build | Vite 7 |
| Styling | Tailwind CSS 4 |
| Backend | FastAPI (Python) |
| Deployment | Docker + nginx |
| PWA | manifest.json + service worker |

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           DGX Server                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐                          │
│  │  dgx-web-ui     │    │  dgx-api        │                          │
│  │  (nginx:3080)   │    │  (FastAPI:3081) │                          │
│  └────────┬────────┘    └────────┬────────┘                          │
│           │                      │                                   │
│           │    ┌─────────────────┼─────────────────┐                 │
│           │    │                 │                 │                 │
│  ┌────────▼────▼──┐   ┌─────────▼───────┐   ┌─────▼───────┐         │
│  │  Ollama        │   │  ComfyUI        │   │  Docker     │         │
│  │  (11434)       │   │  (8188)         │   │  Socket     │         │
│  └────────────────┘   └─────────────────┘   └─────────────┘         │
│                                                                      │
│  ┌────────────────┐   ┌─────────────────┐   ┌─────────────┐         │
│  │  Ultravox      │   │  Chatterbox     │   │  Claude     │         │
│  │  (8100)        │   │  TTS (8004)     │   │  Code CLI   │         │
│  └────────────────┘   └─────────────────┘   └─────────────┘         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Structure

```
src/
├── App.vue                    # Root component, tab routing
├── main.js                    # Vue app initialization
├── config.js                  # Runtime config loader
├── style.css                  # Tailwind imports + custom styles
├── components/
│   ├── Dashboard.vue          # Overview tab
│   ├── Chat.vue               # Ollama chat
│   ├── ImageGenerator.vue     # SDXL/Flux generation
│   ├── VideoGenerator.vue     # LTX Video generation
│   ├── VoiceChat.vue          # Ultravox + Chatterbox
│   ├── AgentChat.vue          # Claude Code integration
│   ├── GooseChat.vue          # Goose research agent
│   ├── Management.vue         # Container management
│   ├── ActivityMonitor.vue    # Header telemetry bar
│   ├── Telemetry.vue          # Detailed telemetry
│   └── Mobile.vue             # Mobile PWA interface
├── composables/
│   ├── useChat.js             # Chat state & API
│   ├── useImageGeneration.js  # Image generation state
│   ├── useVideoGeneration.js  # Video generation state
│   ├── useAgent.js            # Claude Code state
│   ├── useManagement.js       # Container management
│   └── useTelemetry.js        # System stats polling
├── constants/
│   └── mobileConstants.js     # Hardware/network config
└── utils/
    └── (utility functions)
```

---

## Backend API (FastAPI)

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/info` | Docker/system info |
| GET | `/api/containers` | List containers |
| GET | `/api/containers/{name}` | Container details |
| POST | `/api/containers/{name}/action` | Start/stop/restart |
| GET | `/api/containers/{name}/logs` | Container logs |
| POST | `/api/claude` | Claude Code execution |
| GET | `/api/claude/sessions` | List saved sessions |
| POST | `/api/claude/sessions` | Save session |
| POST | `/api/goose` | Goose execution |
| GET | `/api/goose/files` | List research files |
| GET | `/api/goose/files/{name}` | Get research content |

### File: `backend/main.py`

Single-file FastAPI application with:
- Docker client via socket mount
- Claude Code CLI integration
- Goose CLI integration
- Session persistence (JSON file)

---

## External Service Integration

### Ollama (LLM)
- **Port**: 11434
- **Endpoint**: `/api/chat`, `/api/generate`
- **Access**: Direct from frontend (CORS enabled)

### ComfyUI (Image/Video)
- **Port**: 8188
- **Endpoint**: `/prompt`, `/history/{id}`, `/queue`
- **Access**: Direct from frontend or via nginx proxy

### Ultravox (Speech LLM)
- **Port**: 8100
- **Endpoint**: `/v1/chat/completions` (OpenAI-compatible)
- **Access**: Direct from frontend

### Chatterbox TTS
- **Port**: 8004
- **Endpoint**: `/tts`, `/voices`
- **Access**: Direct from frontend

---

## Configuration

### Runtime Config (`public/config.js`)
```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: 'http://localhost:11005',
  OLLAMA_URL: 'http://localhost:11434',
  ULTRAVOX_URL: 'http://localhost:11100',
  CHATTERBOX_URL: 'http://localhost:11004',
  TELEMETRY_URL: 'http://localhost:11006',
  APP_NAME: 'DGX Spark UI',
  VERSION: '1.0.0'
}
```

### Production Config (`config.dgx.js`)
Uses nginx proxy paths (`/comfyui`, `/ollama`, etc.)

---

## Deployment

### Docker Compose

```yaml
services:
  web-ui:
    image: dgx-web-ui
    ports: ["3080:80"]

  api:
    image: dgx-api
    ports: ["3081:8000"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Build Process

1. `npm run build` - Vite production build
2. `docker build` - Multi-stage build (node → nginx)
3. `deploy.sh` - rsync + docker compose

---

## Data Flow Patterns

### Chat Flow
```
User Input → Chat.vue → useChat.js → fetch(Ollama) → Stream → UI Update
```

### Image Generation Flow
```
Submit → ImageGenerator.vue → useImageGeneration.js → POST /prompt
  → Poll /history → Download from /output
```

### Container Management Flow
```
Action → Management.vue → useManagement.js → POST /api/containers/{name}/action
  → Refresh container list
```

---

## Known Limitations

1. **No Authentication**: All endpoints are public
2. **Polling-based**: Telemetry uses 1s polling, not WebSocket
3. **Single User**: No concurrent session isolation
4. **Docker Socket**: Requires privileged access on host
