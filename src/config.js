// Access runtime config from window.DGX_CONFIG
// Falls back to localhost tunnel ports for local development

const defaultConfig = {
  COMFYUI_URL: 'http://localhost:11005',
  OLLAMA_URL: 'http://localhost:11434',
  ULTRAVOX_URL: 'http://localhost:11100',
  CHATTERBOX_URL: 'http://localhost:11004',
  TELEMETRY_URL: 'http://localhost:11006',
  APP_NAME: 'DGX Spark UI',
  VERSION: '1.0.0'
}

export function useConfig() {
  const config = window.DGX_CONFIG || defaultConfig
  return {
    comfyuiUrl: config.COMFYUI_URL,
    ollamaUrl: config.OLLAMA_URL,
    ultravoxUrl: config.ULTRAVOX_URL,
    chatterboxUrl: config.CHATTERBOX_URL,
    telemetryUrl: config.TELEMETRY_URL,
    appName: config.APP_NAME,
    version: config.VERSION
  }
}

export default useConfig
