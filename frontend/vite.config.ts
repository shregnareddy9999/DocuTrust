import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react() as unknown as Plugin],
  server: {
    port: 5173,
    open: '/',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})