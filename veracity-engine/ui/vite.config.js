import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  optimizeDeps: {
    include: ["react-force-graph-2d", "neo4j-driver"],
  },
  build: {
    commonjsOptions: {
      include: [/react-force-graph-2d/, /neo4j-driver/]
    }
  }
})
