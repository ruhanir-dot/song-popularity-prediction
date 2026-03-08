import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/predict_single': 'http://localhost:5001',
      '/predict_batch': 'http://localhost:5001',
      '/get_metrics': 'http://localhost:5001',
      '/run_validation': 'http://localhost:5001',
    }
  }
})
