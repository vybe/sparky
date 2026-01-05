// Runtime configuration for DGX Spark Web UI
// This file is loaded at runtime and can be modified without rebuilding

window.DGX_CONFIG = {
  // API endpoints - tunnel ports for local Mac development
  // When deployed on DGX, config.dgx.js is used instead with nginx proxies
  COMFYUI_URL: 'http://localhost:11005',
  OLLAMA_URL: 'http://localhost:11434',
  ULTRAVOX_URL: 'http://localhost:11100',
  CHATTERBOX_URL: 'http://localhost:11004',
  TELEMETRY_URL: 'http://localhost:11006',

  // App info
  APP_NAME: 'DGX Spark UI',
  VERSION: '1.0.0'
};
