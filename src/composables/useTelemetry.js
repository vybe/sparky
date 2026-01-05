import { ref, toRaw, onMounted, onUnmounted } from 'vue'
import { useConfig } from '../config.js'
import uPlot from 'uplot'

const { telemetryUrl: TELEMETRY_URL, ollamaUrl: OLLAMA_URL } = useConfig()

const MAX_POINTS = 60

export function useTelemetry() {
  const systemStats = ref(null)
  const ollamaLoadedModels = ref([])
  const topProcesses = ref({ top_cpu: [], top_memory: [], gpu_processes: [] })
  const statsLoading = ref(true)

  // Chart tracking
  const timestamps = ref([])
  const cpuHistory = ref([])
  const memHistory = ref([])
  const gpuTempHistory = ref([])

  // Chart refs and instances
  const cpuChartEl = ref(null)
  const memChartEl = ref(null)
  const gpuChartEl = ref(null)
  let cpuChart = null
  let memChart = null
  let gpuChart = null
  let statsInterval = null

  function initHistory() {
    const now = Date.now() / 1000
    for (let i = MAX_POINTS - 1; i >= 0; i--) {
      timestamps.value.push(now - (i * 5))
      cpuHistory.value.push(null)
      memHistory.value.push(null)
      gpuTempHistory.value.push(null)
    }
  }

  function createMobileChartOpts(color, yMax = 100) {
    return {
      width: 300,
      height: 60,
      padding: [4, 2, 4, 2],
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
          fill: color + '30',
          spanGaps: true,
          points: { show: false }
        }
      ]
    }
  }

  function initCharts() {
    if (!cpuChartEl.value || !memChartEl.value || !gpuChartEl.value) return

    cpuChartEl.value.innerHTML = ''
    memChartEl.value.innerHTML = ''
    gpuChartEl.value.innerHTML = ''

    const data = [toRaw(timestamps.value), toRaw(cpuHistory.value)]
    cpuChart = new uPlot(createMobileChartOpts('#3b82f6', 100), data, cpuChartEl.value)

    const memData = [toRaw(timestamps.value), toRaw(memHistory.value)]
    memChart = new uPlot(createMobileChartOpts('#a855f7', 100), memData, memChartEl.value)

    const gpuData = [toRaw(timestamps.value), toRaw(gpuTempHistory.value)]
    gpuChart = new uPlot(createMobileChartOpts('#f97316', 80), gpuData, gpuChartEl.value)

    setTimeout(resizeCharts, 100)
  }

  function updateCharts() {
    if (cpuChart) cpuChart.setData([toRaw(timestamps.value), toRaw(cpuHistory.value)])
    if (memChart) memChart.setData([toRaw(timestamps.value), toRaw(memHistory.value)])
    if (gpuChart) gpuChart.setData([toRaw(timestamps.value), toRaw(gpuTempHistory.value)])
  }

  function resizeCharts() {
    if (!cpuChartEl.value) return
    const width = cpuChartEl.value.parentElement?.clientWidth || 300
    const chartWidth = Math.min(width - 20, 400)
    if (cpuChart) cpuChart.setSize({ width: chartWidth, height: 60 })
    if (memChart) memChart.setSize({ width: chartWidth, height: 60 })
    if (gpuChart) gpuChart.setSize({ width: chartWidth, height: 60 })
  }

  async function loadStats(apiBaseUrl) {
    try {
      const [sysRes, ollamaRes, processRes] = await Promise.all([
        fetch(`${TELEMETRY_URL}/stats`, { signal: AbortSignal.timeout(3000) }).catch(() => null),
        fetch(`${OLLAMA_URL}/api/ps`, { signal: AbortSignal.timeout(3000) }).catch(() => null),
        fetch(`${apiBaseUrl}/processes?limit=5`, { signal: AbortSignal.timeout(3000) }).catch(() => null)
      ])

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

      if (ollamaRes?.ok) {
        const data = await ollamaRes.json()
        ollamaLoadedModels.value = data.models || []
      }

      if (processRes?.ok) {
        topProcesses.value = await processRes.json()
      }

      statsLoading.value = false

      if (!cpuChart && cpuChartEl.value) {
        await new Promise(resolve => setTimeout(resolve, 0))
        initCharts()
      }
    } catch (e) {
      statsLoading.value = false
    }
  }

  function startPolling(apiBaseUrl) {
    initHistory()
    loadStats(apiBaseUrl)
    statsInterval = setInterval(() => loadStats(apiBaseUrl), 5000)
  }

  function stopPolling() {
    if (statsInterval) {
      clearInterval(statsInterval)
      statsInterval = null
    }
  }

  function cleanup() {
    stopPolling()
    if (cpuChart) cpuChart.destroy()
    if (memChart) memChart.destroy()
    if (gpuChart) gpuChart.destroy()
  }

  return {
    // State
    systemStats,
    ollamaLoadedModels,
    topProcesses,
    statsLoading,
    cpuChartEl,
    memChartEl,
    gpuChartEl,
    // Methods
    startPolling,
    stopPolling,
    initCharts,
    resizeCharts,
    cleanup
  }
}
