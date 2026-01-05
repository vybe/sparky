<script setup>
import { ref, toRaw, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useConfig } from '../config.js'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

const { telemetryUrl: TELEMETRY_URL, ollamaUrl: OLLAMA_URL } = useConfig()

// Chart containers
const cpuChartEl = ref(null)
const memChartEl = ref(null)
const gpuChartEl = ref(null)

// uPlot instances
let cpuChart = null
let memChart = null
let gpuChart = null

// History data (last 60 samples = 5 minutes at 5s intervals)
const MAX_POINTS = 60
const timestamps = ref([])
const cpuHistory = ref([])
const memHistory = ref([])
const gpuTempHistory = ref([])

// Current stats
const systemStats = ref(null)
const ollamaStats = ref(null)
const loading = ref(true)
const lastUpdate = ref(null)

let pollInterval = null

// Initialize with empty data
function initHistory() {
  const now = Date.now() / 1000
  for (let i = MAX_POINTS - 1; i >= 0; i--) {
    timestamps.value.push(now - (i * 5))
    cpuHistory.value.push(null)
    memHistory.value.push(null)
    gpuTempHistory.value.push(null)
  }
}

// Minimal chart options - small sparkline style
function createChartOpts(color, yMax = 100) {
  return {
    width: 200,
    height: 40,
    padding: [2, 0, 2, 0],
    cursor: { show: false },
    legend: { show: false },
    select: { show: false },
    scales: {
      x: { time: false },
      y: { min: 0, max: yMax, range: [0, yMax] }
    },
    axes: [
      { show: false },
      { show: false }
    ],
    series: [
      {},
      {
        stroke: color,
        width: 2,
        fill: color + '50',
        spanGaps: true,
        points: { show: false }
      }
    ]
  }
}

function initCharts() {
  if (!cpuChartEl.value || !memChartEl.value || !gpuChartEl.value) return

  // Clear any existing content
  cpuChartEl.value.innerHTML = ''
  memChartEl.value.innerHTML = ''
  gpuChartEl.value.innerHTML = ''

  // Convert Vue reactive arrays to raw arrays for uPlot
  const data = [toRaw(timestamps.value), toRaw(cpuHistory.value)]
  cpuChart = new uPlot(createChartOpts('#3b82f6', 100), data, cpuChartEl.value)

  const memData = [toRaw(timestamps.value), toRaw(memHistory.value)]
  memChart = new uPlot(createChartOpts('#a855f7', 100), memData, memChartEl.value)

  const gpuData = [toRaw(timestamps.value), toRaw(gpuTempHistory.value)]
  gpuChart = new uPlot(createChartOpts('#f97316', 80), gpuData, gpuChartEl.value)

  // Resize after mount
  setTimeout(handleResize, 50)
}

function updateCharts() {
  if (cpuChart) cpuChart.setData([toRaw(timestamps.value), toRaw(cpuHistory.value)])
  if (memChart) memChart.setData([toRaw(timestamps.value), toRaw(memHistory.value)])
  if (gpuChart) gpuChart.setData([toRaw(timestamps.value), toRaw(gpuTempHistory.value)])
}

async function fetchStats() {
  try {
    const sysRes = await fetch(`${TELEMETRY_URL}/stats`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (sysRes?.ok) {
      systemStats.value = await sysRes.json()

      const now = Date.now() / 1000
      timestamps.value.push(now)
      cpuHistory.value.push(systemStats.value.cpu?.percent ?? null)
      memHistory.value.push(systemStats.value.memory?.percent ?? null)
      gpuTempHistory.value.push(systemStats.value.gpu?.temp ?? null)

      if (timestamps.value.length > MAX_POINTS) {
        timestamps.value.shift()
        cpuHistory.value.shift()
        memHistory.value.shift()
        gpuTempHistory.value.shift()
      }

      updateCharts()
    }

    const ollamaRes = await fetch(`${OLLAMA_URL}/api/ps`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (ollamaRes?.ok) {
      const data = await ollamaRes.json()
      ollamaStats.value = {
        models: data.models || [],
        count: data.models?.length || 0
      }
    }

    lastUpdate.value = new Date()
    loading.value = false
  } catch (e) {
    loading.value = false
  }
}

function formatBytes(gb) {
  return gb?.toFixed(1) || '0'
}

function formatPercent(pct) {
  return pct?.toFixed(0) || '0'
}

function handleResize() {
  const width = cpuChartEl.value?.parentElement?.clientWidth
  if (!width) return

  const chartWidth = Math.min(width - 100, 200)
  if (cpuChart) cpuChart.setSize({ width: chartWidth, height: 40 })
  if (memChart) memChart.setSize({ width: chartWidth, height: 40 })
  if (gpuChart) gpuChart.setSize({ width: chartWidth, height: 40 })
}

// Watch for loading to become false, then init charts
watch(loading, async (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    await nextTick()
    initCharts()
  }
})

onMounted(async () => {
  initHistory()
  await fetchStats()
  pollInterval = setInterval(fetchStats, 5000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (cpuChart) cpuChart.destroy()
  if (memChart) memChart.destroy()
  if (gpuChart) gpuChart.destroy()
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div class="activity-monitor">
    <div v-if="loading" class="text-gray-500 text-xs py-2 text-center">Loading...</div>

    <div v-else class="monitor-grid">
      <!-- CPU -->
      <div class="stat-row">
        <div class="stat-label">
          <span class="dot bg-blue-500"></span>
          <span>CPU</span>
        </div>
        <div ref="cpuChartEl" class="chart-box"></div>
        <div class="stat-value text-blue-400">{{ formatPercent(systemStats?.cpu?.percent) }}%</div>
      </div>

      <!-- Memory -->
      <div class="stat-row">
        <div class="stat-label">
          <span class="dot bg-purple-500"></span>
          <span>Mem</span>
        </div>
        <div ref="memChartEl" class="chart-box"></div>
        <div class="stat-value text-purple-400">{{ formatBytes(systemStats?.memory?.used) }}<span class="text-gray-500">/{{ formatBytes(systemStats?.memory?.total) }}G</span></div>
      </div>

      <!-- GPU -->
      <div class="stat-row">
        <div class="stat-label">
          <span class="dot bg-orange-500"></span>
          <span>GPU</span>
        </div>
        <div ref="gpuChartEl" class="chart-box"></div>
        <div class="stat-value" :class="(systemStats?.gpu?.temp ?? 0) > 70 ? 'text-red-400' : 'text-orange-400'">
          {{ systemStats?.gpu?.temp ?? '-' }}°<span class="text-gray-500 ml-1">{{ systemStats?.gpu?.power ?? '-' }}W</span>
        </div>
      </div>

      <!-- Disk (no chart, just bar) -->
      <div class="stat-row">
        <div class="stat-label">
          <span class="dot bg-green-500"></span>
          <span>Disk</span>
        </div>
        <div class="disk-bar">
          <div class="disk-fill" :style="{ width: `${systemStats?.disk?.percent || 0}%` }"></div>
        </div>
        <div class="stat-value text-green-400">{{ formatPercent(systemStats?.disk?.percent) }}%</div>
      </div>

      <!-- Ollama -->
      <div v-if="ollamaStats?.count" class="stat-row ollama-row">
        <div class="stat-label">
          <span class="dot bg-yellow-500"></span>
          <span>Ollama</span>
        </div>
        <div class="ollama-models">
          {{ ollamaStats.models.map(m => m.name.split(':')[0]).join(', ') }}
        </div>
        <div class="stat-value text-yellow-400">{{ ollamaStats.count }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.activity-monitor {
  background: rgba(17, 24, 39, 0.8);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
}

.monitor-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 280px;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9ca3af;
  width: 50px;
  flex-shrink: 0;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chart-box {
  flex: 1;
  height: 40px;
  min-width: 100px;
  max-width: 200px;
  background: rgba(31, 41, 55, 0.5);
  border-radius: 4px;
  overflow: hidden;
}

.stat-value {
  font-weight: 600;
  font-family: ui-monospace, monospace;
  min-width: 70px;
  text-align: right;
}

.disk-bar {
  flex: 1;
  height: 8px;
  min-width: 100px;
  max-width: 200px;
  background: #374151;
  border-radius: 4px;
  overflow: hidden;
}

.disk-fill {
  height: 100%;
  background: #22c55e;
  transition: width 0.3s ease;
}

.ollama-row {
  width: 100%;
}

.ollama-models {
  flex: 1;
  color: #6b7280;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* uPlot canvas styling */
:deep(.uplot) {
  width: 100% !important;
}

:deep(.u-wrap) {
  width: 100% !important;
}

:deep(.u-over),
:deep(.u-under) {
  width: 100% !important;
}
</style>
