import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5176,
    strictPort: true,
    // Add allowedHosts to permit Cloudflare Tunnel requests:
    allowedHosts: [
      'skillinex.hacksmiths.dev',
      '.hacksmiths.dev', // Allows any subdomain under hacksmiths.dev
    ],
  },
})