# Feature: Container Management

## Overview
System monitoring and Docker container/service management for DGX services.

## User Story
As an administrator, I want to monitor system resources and manage containers so that I can ensure services are running properly.

## Entry Points
- **UI**: `src/components/Management.vue:162` - System dashboard
- **API**: FastAPI backend at `/api/*`

## Frontend Layer

### Components
- `src/components/Management.vue:178-227` - System Overview (Docker, GPU, Memory, Disk)
- `src/components/Management.vue:229-297` - Top Processes (GPU, Memory, CPU)
- `src/components/Management.vue:299-386` - Trinity Agent Platform section
- `src/components/Management.vue:388-427` - Managed Services grid
- `src/components/Management.vue:429-509` - All Containers table
- `src/components/Management.vue:512-525` - Logs Modal

### Composables
- `src/composables/useManagement.js:3-167` - Used by Mobile.vue

**Key State:**
```javascript
services        // ref([]) - Managed services with status
containers      // ref([]) - All Docker containers
systemInfo      // ref(null) - Docker and host info
gpuStats        // ref(null) - GPU utilization, memory, temp
diskStats       // ref(null) - Disk usage
processes       // ref({ top_cpu: [], top_memory: [], gpu_processes: [] })
trinity         // ref({ services: [], version: null })
actionLoading   // ref({}) - Loading states for actions
logs            // ref({ container, content, visible }) - Logs modal
```

### API Calls

**Load All Data:**
```javascript
// src/components/Management.vue:35-43
const [servicesData, containersData, infoData, gpuData, diskData, processData, trinityData] = await Promise.all([
  fetchApi('/services'),
  fetchApi('/containers?all=true'),
  fetchApi('/info'),
  fetchApi('/gpu'),
  fetchApi('/disk'),
  fetchApi('/processes?limit=8'),
  fetchApi('/trinity/status')
])
```

**Container Actions:**
```javascript
// src/components/Management.vue:95-98
await fetchApi(`/containers/${containerName}/action`, {
  method: 'POST',
  body: JSON.stringify({ action }) // 'start' | 'stop' | 'restart'
})
```

**Service Restart:**
```javascript
// src/components/Management.vue:111
await fetchApi(`/services/${serviceName}/restart`, { method: 'POST' })
```

**View Logs:**
```javascript
// src/components/Management.vue:123
const data = await fetchApi(`/containers/${containerName}/logs?lines=200`)
```

## Backend Layer

### FastAPI Endpoints (`backend/main.py`)

| Endpoint | Method | Line | Purpose |
|----------|--------|------|---------|
| `/api/info` | GET | 119 | Docker and system info |
| `/api/containers` | GET | 140 | List all containers |
| `/api/containers/{name}/action` | POST | 187 | Start/stop/restart container |
| `/api/containers/{name}/logs` | GET | 211 | Get container logs |
| `/api/services` | GET | 240 | List managed services + Ollama |
| `/api/services/{name}/restart` | POST | 273 | Restart service |
| `/api/gpu` | GET | 352 | GPU stats via nvidia-smi |
| `/api/disk` | GET | 383 | Disk usage via df |
| `/api/processes` | GET | 406 | Top processes by CPU/memory |
| `/api/trinity/status` | GET | 474 | Trinity services status |
| `/api/trinity/update` | POST | 509 | Pull and restart Trinity |
| `/api/trinity/restart` | POST | 570 | Restart Trinity containers |

### Managed Services (`backend/main.py:37-45`)
```python
MANAGED_SERVICES = {
    "comfyui": {"container": "comfyui", "description": "Image/Video generation"},
    "open-webui": {"container": "open-webui", "description": "Chat interface"},
    "chatterbox": {"container": "chatterbox-tts-server-cu128", "description": "Text-to-speech"},
    "ultravox": {"container": "ultravox-vllm", "description": "Speech LLM"},
    "trinity-backend": {"container": "trinity-backend", "description": "Trinity API"},
    "trinity-frontend": {"container": "trinity-frontend", "description": "Trinity UI"},
    "trinity-mcp": {"container": "trinity-mcp", "description": "Trinity MCP Server"},
}
```

### External Commands

**GPU Stats:**
```python
# backend/main.py:356-360
subprocess.run([
    "nvidia-smi",
    "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
    "--format=csv,noheader,nounits"
])
```

**Ollama Status:**
```python
# backend/main.py:226-238
subprocess.run(["pgrep", "-f", "ollama.*serve"])
```

## Data Flow

1. **On Mount**: `loadAll()` fetches all data in parallel
2. **Every 15s**: `setInterval(loadAll, 15000)` refreshes data
3. **Action click**: `performAction()` or `restartService()` called
4. **Backend executes**: Docker SDK or subprocess command
5. **Refresh**: `loadAll()` called after action completes
6. **UI updates**: Reactive state triggers re-render

```
Management.vue --> loadAll() --> Promise.all([
                                   /api/services
                                   /api/containers
                                   /api/info
                                   /api/gpu
                                   /api/disk
                                   /api/processes
                                   /api/trinity/status
                                 ])
                                    |
                              Update state
                                    |
                              Render dashboard
```

## Docker Integration

**Connection:**
```python
# backend/main.py:34
client = docker.from_env()  # Uses /var/run/docker.sock
```

**Container Operations:**
```python
container = client.containers.get(container_name)
container.start()
container.stop(timeout=10)
container.restart(timeout=10)
container.logs(tail=lines, timestamps=True)
```

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| API timeout | Fetch fails | Error banner | Dismiss + Retry |
| Container not found | 404 from backend | Error in banner | Refresh |
| Action fails | Error from backend | Error message | Retry |
| Docker offline | Backend exception | 500 error | Check Docker |

## Configuration

- **Backend runs on**: Port 8080 (proxied via nginx to `/api`)
- **Docker socket**: Mounted at `/var/run/docker.sock`
- **Refresh interval**: 15 seconds

## Trinity-Specific Features

**Update Process:**
1. `git pull origin main` in ~/trinity
2. `docker compose down`
3. `docker compose up -d`
4. Return new version from git log

**Services:**
- trinity-backend (port 8000 -> 11080)
- trinity-frontend (port 3000 -> 11030)
- trinity-mcp (port 8180 -> 11085)

## Related Flows

- **Downstream**: Chat, Image, Video, Voice depend on managed services
- **Upstream**: Telemetry provides real-time stats
