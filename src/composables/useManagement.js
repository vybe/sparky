import { ref } from 'vue'

export function useManagement(apiBaseUrl) {
  const managementServices = ref([])
  const containers = ref([])
  const trinity = ref({ services: [], version: null })
  const trinityUpdating = ref(false)
  const trinityUpdateResult = ref(null)
  const managementLoading = ref(true)
  const actionLoading = ref({})
  const managementError = ref('')
  const logsModal = ref({ visible: false, container: '', content: '' })

  async function fetchManagementApi(endpoint, options = {}) {
    const res = await fetch(`${apiBaseUrl}${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers }
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'API error')
    }
    return res.json()
  }

  async function loadManagement() {
    managementLoading.value = true
    managementError.value = ''
    try {
      const [servicesData, containersData, trinityData] = await Promise.all([
        fetchManagementApi('/services'),
        fetchManagementApi('/containers?all=true'),
        fetchManagementApi('/trinity/status').catch(() => ({ services: [], version: null }))
      ])
      managementServices.value = (servicesData.services || []).filter(s => !s.name.startsWith('trinity-'))
      containers.value = containersData.containers || []
      trinity.value = trinityData
    } catch (e) {
      managementError.value = e.message
    } finally {
      managementLoading.value = false
    }
  }

  async function updateTrinity() {
    if (trinityUpdating.value) return
    trinityUpdating.value = true
    trinityUpdateResult.value = null
    try {
      const result = await fetchManagementApi('/trinity/update', { method: 'POST' })
      trinityUpdateResult.value = result
      if (result.success) {
        const trinityData = await fetchManagementApi('/trinity/status').catch(() => ({ services: [], version: null }))
        trinity.value = trinityData
      }
    } catch (e) {
      trinityUpdateResult.value = { success: false, error: e.message }
    } finally {
      trinityUpdating.value = false
    }
  }

  async function restartTrinity() {
    actionLoading.value['trinity-restart'] = true
    try {
      await fetchManagementApi('/trinity/restart', { method: 'POST' })
      await loadManagement()
    } catch (e) {
      managementError.value = `Failed to restart Trinity: ${e.message}`
    } finally {
      actionLoading.value['trinity-restart'] = false
    }
  }

  async function performAction(containerName, action) {
    const key = `${containerName}-${action}`
    actionLoading.value[key] = true
    try {
      await fetchManagementApi(`/containers/${containerName}/action`, {
        method: 'POST',
        body: JSON.stringify({ action })
      })
      await loadManagement()
    } catch (e) {
      managementError.value = `Failed to ${action} ${containerName}: ${e.message}`
    } finally {
      actionLoading.value[key] = false
    }
  }

  async function restartService(serviceName) {
    actionLoading.value[`service-${serviceName}-restart`] = true
    try {
      await fetchManagementApi(`/services/${serviceName}/restart`, { method: 'POST' })
      await loadManagement()
    } catch (e) {
      managementError.value = `Failed to restart ${serviceName}: ${e.message}`
    } finally {
      actionLoading.value[`service-${serviceName}-restart`] = false
    }
  }

  async function startService(serviceName) {
    actionLoading.value[`service-${serviceName}-start`] = true
    try {
      await fetchManagementApi(`/services/${serviceName}/start`, { method: 'POST' })
      await loadManagement()
    } catch (e) {
      managementError.value = `Failed to start ${serviceName}: ${e.message}`
    } finally {
      actionLoading.value[`service-${serviceName}-start`] = false
    }
  }

  async function stopService(serviceName) {
    actionLoading.value[`service-${serviceName}-stop`] = true
    try {
      await fetchManagementApi(`/services/${serviceName}/stop`, { method: 'POST' })
      await loadManagement()
    } catch (e) {
      managementError.value = `Failed to stop ${serviceName}: ${e.message}`
    } finally {
      actionLoading.value[`service-${serviceName}-stop`] = false
    }
  }

  async function viewLogs(containerName) {
    logsModal.value = { visible: true, container: containerName, content: 'Loading...' }
    try {
      const data = await fetchManagementApi(`/containers/${containerName}/logs?lines=100`)
      logsModal.value.content = data.logs || 'No logs available'
    } catch (e) {
      logsModal.value.content = `Error: ${e.message}`
    }
  }

  function getStatusClass(status) {
    switch (status) {
      case 'running': return 'status-running'
      case 'exited': return 'status-stopped'
      default: return 'status-unknown'
    }
  }

  return {
    // State
    managementServices,
    containers,
    trinity,
    trinityUpdating,
    trinityUpdateResult,
    managementLoading,
    actionLoading,
    managementError,
    logsModal,
    // Methods
    loadManagement,
    updateTrinity,
    restartTrinity,
    performAction,
    restartService,
    startService,
    stopService,
    viewLogs,
    getStatusClass
  }
}
