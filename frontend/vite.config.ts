// ARCHITECTURE §16.1 / D-20: dev proxies /api to FastAPI; the demo serves dist/ from FastAPI.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { outDir: 'dist' },
})
