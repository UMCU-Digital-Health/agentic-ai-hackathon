/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The @tabler/icons-react barrel pulls a very large module graph; pre-bundling
  // it once keeps the first dev-server load quick. Production builds tree-shake
  // either way, so this is a dev-experience fix only.
  optimizeDeps: { include: ['@tabler/icons-react'] },
  server: {
    port: 5173,
    strictPort: true,
    // The API is fixed on 8080. Proxying means the client only ever calls
    // relative paths and CORS never enters the picture in dev.
    // 127.0.0.1, not localhost: Node resolves localhost to ::1 first, while
    // uvicorn binds 0.0.0.0 (IPv4 only), which surfaces as a 502 ECONNREFUSED.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/unit/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['tests/e2e/**', 'node_modules/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/vite-env.d.ts', 'src/api/schema.d.ts'],
    },
  },
})
