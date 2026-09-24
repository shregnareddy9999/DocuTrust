import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react() as unknown as Plugin],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})