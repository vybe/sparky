# DGX Spark Web UI

Vue 3 + Vite web interface for DGX Spark services. Runs as a Docker container with nginx.

## Features

- **Image Generation** - SDXL models (Pony, NoobAI, Illustrious) and Flux via ComfyUI
- **Video Generation** - LTX Video 2B/13B via ComfyUI
- **Chat** - Streaming chat with Ollama LLMs
- **Voice Chat** - Voice-in/voice-out with Ultravox + Chatterbox TTS
- **Telemetry** - Real-time GPU, CPU, memory, disk monitoring
- **Management** - Docker container control (start/stop/restart/logs)
- **PWA Mobile App** - Mobile-optimized interface, installable as home screen app

## Prerequisites

### Required Services

The web UI requires these services to be running on your DGX/server:

1. **Ollama** - LLM inference engine (port 11434)
2. **ComfyUI** - Image/video generation (port 8188)
3. **Ultravox** - Speech LLM (port 8100)
4. **Chatterbox TTS** - Text-to-speech (port 8004)
5. **Telemetry API** - System stats (port 8006)

### Ollama CORS Configuration

Ollama must allow cross-origin requests:

```bash
# If using snap:
sudo snap set ollama origins='*'
sudo snap restart ollama

# If using systemd:
# Edit /etc/systemd/system/ollama.service and add:
# Environment="OLLAMA_ORIGINS=*"
# Then: sudo systemctl daemon-reload && sudo systemctl restart ollama
```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/vybe/sparky
cd sparky
```

### 2. Configure Deployment

Copy the example files:

```bash
cp .env.example .env
chmod +x deploy.sh
```

Edit `.env` with your server details:

```bash
DGX_HOST=your-server-ip          # Your DGX/server IP or hostname
DGX_USER=your-username           # SSH username
DGX_PASS=your-password          # SSH password (or use SSH keys)
REMOTE_DIR=/home/$USER/dgx-web-ui  # Optional: custom deployment path
```

### 3. Configure for Your Instance

**Important:** The UI displays hardware specs and network info. Update these for your system:

#### Edit `src/constants/mobileConstants.js`:

```javascript
export const network = {
  local: { name: 'Local', ip: '192.168.1.XXX' },    // Your local IP
  vpn: { name: 'VPN', ip: '100.XXX.XXX.XXX' }      // Your VPN IP (if applicable)
}

export const hardware = {
  gpu: { name: 'Your GPU', arch: 'Architecture', compute: 'Specs' },
  cpu: { name: 'Your CPU', detail: 'Details' },
  memory: { size: 'XX GB', type: 'Type', bandwidth: 'XXX GB/s' },
  storage: { size: 'X TB', free: '~X.X TB' }
}

export const availableModels = {
  llm: ['model1', 'model2'],       // Your installed LLM models
  video: ['video-model'],          // Your video generation models
  image: ['image-model'],          // Your image generation models
  audio: ['audio-model']           // Your audio models
}
```

#### Edit `src/components/Dashboard.vue` (lines 8-94):

Update the same `network`, `hardware`, and `models` objects to match your system.

**Tip:** Search for `192.168.1.` and `100.xxx.` to find all places to update IPs.

### 4. Verify Service Ports

Ensure these services are accessible on your server:

| Service | Default Port | How to Check |
|---------|-------------|--------------|
| Ollama | 11434 | `curl http://localhost:11434/api/version` |
| ComfyUI | 8188 | `curl http://localhost:8188/system_stats` |
| Ultravox | 8100 | `curl http://localhost:8100/v1/models` |
| Chatterbox | 8004 | `curl http://localhost:8004/voices` |
| Telemetry | 8006 | `curl http://localhost:8006/stats` |

If your ports differ, update `config.dgx.js` and `nginx.conf` accordingly.

### 5. Deploy

```bash
./deploy.sh deploy
```

The web UI will be available at:
- Web UI: `http://your-server-ip:3080`
- API: `http://your-server-ip:3081/docs`

### 6. Access Mobile View

Add `?mobile=1` to the URL: `http://your-server-ip:3080/?mobile=1`

On iOS, use Safari → Share → Add to Home Screen for a standalone app experience.

## Configuration Checklist

Before deploying, ensure you've configured:

- [ ] `.env` file with your server credentials
- [ ] `deploy.sh` copied and made executable
- [ ] Network IPs updated in `src/constants/mobileConstants.js`
- [ ] Network IPs updated in `src/components/Dashboard.vue`
- [ ] Hardware specs updated for your system
- [ ] Model lists updated based on your installations
- [ ] Service ports verified and accessible
- [ ] Ollama CORS configured (see above)

## Customizing for Your System

**📖 See [CONFIGURATION.md](CONFIGURATION.md) for the complete configuration guide** covering:
- Network IPs and VPN setup
- Hardware specifications display
- Model lists (LLM, image, video, audio)
- Service ports and links
- Backend API customization
- Docker Compose settings

**For advanced customization, see [SETUP.md](SETUP.md)**

## Local Development

For local development with API tunneling:

```bash
# Install dependencies
npm install

# Run dev server
npm run dev
# Open http://localhost:3000
```

The development server expects services to be accessible on localhost ports (typically via SSH tunneling).

## Configuration

Runtime config is loaded from `window.DGX_CONFIG` (defined in `public/config.js` or `config.dgx.js`).

**Local development** (`public/config.js`):
```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: 'http://localhost:11005',
  OLLAMA_URL: 'http://localhost:11434',
  ULTRAVOX_URL: 'http://localhost:11100',
  CHATTERBOX_URL: 'http://localhost:11004',
  TELEMETRY_URL: 'http://localhost:11006',
  APP_NAME: 'DGX Spark UI',
  VERSION: '1.0.0'
};
```

**Production** (`config.dgx.js`):
Uses nginx proxies - all services accessed via relative paths like `/comfyui`, `/ollama`, etc.

## Architecture

### Frontend
- Vue 3 with Composition API
- Vite 7 for build tooling
- Tailwind CSS 4 for styling
- PWA support (manifest + service worker)

### Backend API
- FastAPI (Python)
- Docker container management
- System monitoring
- Claude Code integration

### Deployment
- Multi-stage Docker build
- Nginx for static file serving
- Docker Compose for orchestration

## Deployment Commands

```bash
./deploy.sh sync      # Sync files only
./deploy.sh build     # Rebuild Docker image
./deploy.sh start     # Start containers
./deploy.sh stop      # Stop containers
./deploy.sh restart   # Restart containers
./deploy.sh logs      # View container logs
./deploy.sh status    # Check container status
./deploy.sh deploy    # Full deployment (sync + build + start)
```

## Service Ports

| Service | Default Port | Purpose |
|---------|-------------|---------|
| Web UI | 3080 | Frontend application |
| API | 3081 | Backend management API |
| ComfyUI | 8188 | Image/video generation |
| Ollama | 11434 | LLM inference |
| Ultravox | 8100 | Speech understanding |
| Chatterbox | 8004 | Text-to-speech |
| Telemetry | 8006 | System stats |

## Documentation

| Document | Purpose |
|----------|---------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Overview and preparation checklist |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Complete configuration guide |
| **[SETUP.md](SETUP.md)** | Advanced setup and customization |
| **[SECURITY.md](SECURITY.md)** | Security best practices and policies |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute to this project |

## Troubleshooting

### Chat Not Working (403 Forbidden)

Ollama CORS is not configured. See [Ollama CORS Configuration](#ollama-cors-configuration) above.

### Images/Videos Not Generating

Check ComfyUI is running:
```bash
sudo docker ps | grep comfyui
sudo docker logs comfyui --tail 50
```

Restart if needed:
```bash
sudo docker restart comfyui
```

### Voice Chat Not Working

Ultravox container must be running with `VLLM_USE_V1=1`:
```bash
sudo docker ps | grep ultravox
sudo docker restart ultravox-vllm
```

### Container Management Not Loading

Backend API must be running:
```bash
sudo docker ps | grep dgx-api
sudo docker logs dgx-api --tail 50
```

## Security Notes

- The backend API requires Docker socket access for container management
- Claude Code integration runs with `--dangerously-skip-permissions` for autonomous execution
- SSH passwords in `.env` should be secured - consider using SSH keys instead
- For production, use a reverse proxy (nginx/Caddy) with HTTPS

## Tech Stack

- Vue 3 + Composition API
- Vite 7
- Tailwind CSS 4
- Docker + nginx (production)
- PWA (manifest + service worker)
- FastAPI (backend)

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- Documentation is updated
- No hardcoded credentials or environment-specific values

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Acknowledgments

Built with [Claude Code](https://claude.com/claude-code)
