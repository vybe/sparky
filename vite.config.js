import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      // Proxy ComfyUI requests
      '/comfyui': {
        target: 'http://localhost:11005',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/comfyui/, '')
      },
      // Proxy Ollama requests
      '/ollama': {
        target: 'http://localhost:11434',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ollama/, '')
      }
    }
  }
})
