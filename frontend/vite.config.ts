// ARCHITECTURE §16.1 / D-20: dev proxies /api to FastAPI; the demo serves dist/ from FastAPI.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: {
    outDir: 'dist',
    // vendor chunks: parsed in parallel and cached across rebuilds of our code
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return undefined
          if (/[\/](recharts|d3-|victory-vendor)/.test(id)) return 'charts'
          if (/[\/](@mantine|@tabler)[\/]/.test(id)) return 'ui'
          if (/[\/](motion|framer-motion|motion-dom|motion-utils)[\/]/.test(id)) return 'motion'
          if (/[\/](react|react-dom|scheduler)[\/]/.test(id)) return 'react'
          return 'vendor'
        },
      },
    },
  },
})
