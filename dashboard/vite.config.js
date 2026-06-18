import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev mode proxies the API to the engine server (python -m engine.cli serve, :8420).
// Build emits to dist/, which the engine serves statically in production.
export default defineConfig({
  plugins: [react()],
  base: './',
  server: { proxy: { '/api': 'http://127.0.0.1:8420' } },
  build: { outDir: 'dist', emptyOutDir: true },
})
