import { dirname } from "path"
import path from "path"
import { fileURLToPath } from "url"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5176,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8088',
      '/health': 'http://127.0.0.1:8088',
    },
    // Add allowedHosts to permit Cloudflare Tunnel requests:
    allowedHosts: [
      'skillinex.hacksmiths.dev',
      '.hacksmiths.dev', // Allows any subdomain under hacksmiths.dev
    ],
  },
})