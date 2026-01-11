# Feature: Telemetry

## Overview
Real-time system monitoring with GPU, CPU, memory, and disk stats using sparkline charts.

## User Story
As a user, I want to see real-time system stats so that I can monitor DGX resource usage.

## Entry Points
- **UI**: `src/components/ActivityMonitor.vue:189` - Compact sparkline view
- **UI**: `src/components/Telemetry.vue:83` - Full stats panel
- **API**: Telemetry API at `http://localhost:11006/stats`

## Frontend Layer

### Components

**ActivityMonitor.vue** (Compact sparkline version)
- `src/components/ActivityMonitor.vue:194-236` - CPU/Mem/GPU rows with charts
- `src/components/ActivityMonitor.vue:239-248` - Ollama loaded models

**Telemetry.vue** (Dashboard panel)
- `src/components/Telemetry.vue:94-162` - Grid of GPU, CPU, Memory, Ollama stats
- `src/components/Telemetry.vue:165-168` - Disk usage row

### Composables
- `src/composables/useTelemetry.js:9-186` - Used by Mobile.vue

**Key State:**
```javascript
systemStats       // ref(null) - { cpu, memory, gpu, disk }
ollamaLoadedModels // ref([]) - Currently loaded models
topProcesses      // ref({ top_cpu: [], top_memory: [], gpu_processes: [] })
timestamps        // ref([]) - X-axis for charts
cpuHistory        // ref([]) - CPU % history (60 points)
memHistory        // ref([]) - Memory % history
gpuTempHistory    // ref([]) - GPU temp history
```

**Chart Refs:**
```javascript
cpuChartEl  // ref(null) - DOM element for CPU chart
memChartEl  // ref(null) - DOM element for memory chart
gpuChartEl  // ref(null) - DOM element for GPU chart
```

### API Calls

**Telemetry Stats:**
```javascript
// src/components/ActivityMonitor.vue:105-107
await fetch(`${TELEMETRY_URL}/stats`, {
  signal: AbortSignal.timeout(3000)
})
// Response:
// {
//   cpu: { percent: 12.5 },
//   memory: { used: 45.2, total: 128, percent: 35.3 },
//   gpu: { temp: 42, power: 15, name: "NVIDIA GB10" },
//   disk: { used: 578, total: 4096, percent: 14.1 }
// }
```

**Ollama Loaded Models:**
```javascript
// src/components/ActivityMonitor.vue:128-130
await fetch(`${OLLAMA_URL}/api/ps`, {
  signal: AbortSignal.timeout(3000)
})
// Response: { models: [{ name: "gpt-oss:120b" }] }
```

**ComfyUI Stats (Telemetry.vue only):**
```javascript
// src/components/Telemetry.vue:19-22
await fetch(`${COMFYUI_URL}/system_stats`, {
  signal: AbortSignal.timeout(3000)
})
// Response: { devices: [{ vram_total, vram_free }], system: { comfyui_version } }
```

## Chart Implementation

### uPlot Library

```javascript
// src/components/ActivityMonitor.vue:4
import uPlot from 'uplot'
```

### Chart Options

```javascript
// src/components/ActivityMonitor.vue:46-72
function createChartOpts(color, yMax = 100) {
  return {
    width: 200,
    height: 40,
    padding: [2, 0, 2, 0],
    cursor: { show: false },
    legend: { show: false },
    scales: {
      x: { time: false },
      y: { min: 0, max: yMax }
    },
    axes: [{ show: false }, { show: false }],
    series: [
      {},
      {
        stroke: color,
        width: 2,
        fill: color + '50',  // Translucent fill
        spanGaps: true,
        points: { show: false }
      }
    ]
  }
}
```

### History Management

```javascript
// src/components/ActivityMonitor.vue:35-43
const MAX_POINTS = 60  // 5 minutes at 5s intervals

function initHistory() {
  const now = Date.now() / 1000
  for (let i = MAX_POINTS - 1; i >= 0; i--) {
    timestamps.value.push(now - (i * 5))
    cpuHistory.value.push(null)
    // ... other histories
  }
}
```

### Chart Updates

```javascript
// src/components/ActivityMonitor.vue:97-101
function updateCharts() {
  if (cpuChart) cpuChart.setData([toRaw(timestamps.value), toRaw(cpuHistory.value)])
  if (memChart) memChart.setData([toRaw(timestamps.value), toRaw(memHistory.value)])
  if (gpuChart) gpuChart.setData([toRaw(timestamps.value), toRaw(gpuTempHistory.value)])
}
```

## Data Flow

1. **On Mount**: `initHistory()` creates empty arrays, `fetchStats()` gets first data
2. **Every 5s**: `setInterval(fetchStats, 5000)` polls for updates
3. **New data**: Push to history arrays, shift if > 60 points
4. **Charts update**: `updateCharts()` passes new data to uPlot
5. **On resize**: `handleResize()` recalculates chart dimensions

```
Mount --> initHistory() --> fetchStats()
                              |
            /stats <--> /api/ps <--> /system_stats
                              |
                        Push to history
                              |
                        updateCharts()
                              |
                        uPlot.setData()
```

## External Services

### Telemetry API (port 8006 / tunnel 11006)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stats` | GET | CPU, memory, GPU, disk stats |

**Response Format:**
```json
{
  "cpu": { "percent": 12.5 },
  "memory": { "used": 45.2, "total": 128, "percent": 35.3 },
  "gpu": { "temp": 42, "power": 15, "name": "NVIDIA GB10" },
  "disk": { "used": 578, "total": 4096, "percent": 14.1 }
}
```

### Ollama API (port 11434)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ps` | GET | List GPU-loaded models |

### ComfyUI API (port 8188 / tunnel 11005)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/system_stats` | GET | VRAM usage, ComfyUI version |

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| API timeout | 3s timeout | Shows "N/A" | Next poll |
| Service offline | Fetch fails | Shows "N/A" | Check Manage tab |
| Chart not ready | null check | Skip update | Retry on next poll |

## Configuration

- **TELEMETRY_URL**: `src/config.js:10` - `http://localhost:11006`
- **OLLAMA_URL**: `src/config.js:7` - `http://localhost:11434`
- **COMFYUI_URL**: `src/config.js:5` - `http://localhost:11005`
- **Poll interval**: 5 seconds
- **History length**: 60 points (5 minutes)

## Visual Design

**Colors:**
- CPU: Blue (#3b82f6)
- Memory: Purple (#a855f7)
- GPU: Orange (#f97316)
- Disk: Green (#22c55e)

**Thresholds:**
- GPU temp > 70C: Red text
- Otherwise: Color-coded by type

## Cleanup

```javascript
// src/components/ActivityMonitor.vue:180-185
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (cpuChart) cpuChart.destroy()
  if (memChart) memChart.destroy()
  if (gpuChart) gpuChart.destroy()
  window.removeEventListener('resize', handleResize)
})
```

## Related Flows

- **Downstream**: Stats inform users about system load for generation tasks
- **Parallel**: Management tab shows similar data in different format
