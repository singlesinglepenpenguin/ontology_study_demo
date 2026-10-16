import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: { __SUPPLIER_DEMO__: JSON.stringify(process.env.ONTOPILOT_SUPPLIER_DEMO === '1') },
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
