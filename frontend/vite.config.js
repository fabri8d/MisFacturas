import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/tests/vitest.setup.js'],
    include: ['src/tests/**/*.test.js'],
    exclude: ['e2e/**', 'node_modules/**'],
    server: {
      deps: {
        inline: ['vuetify'],
      },
    },
    css: false,
  },
})
