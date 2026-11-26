import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

const harness = process.env.HARNESS_URL ?? 'http://127.0.0.1:8765'

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 5199,
    strictPort: true,
    proxy: { '/ws': { target: harness, ws: true } },
  },
})
