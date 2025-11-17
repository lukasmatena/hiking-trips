import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  server: {
    proxy: {
      // This rule proxies any request starting with /api
      // to the backend server.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false // The backend is not HTTPS
      }
    }
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        detail: resolve(__dirname, 'detail.html')
      }
    }
  }
})