import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname),
      '@src': path.resolve(__dirname, 'src'),
      '@components': path.resolve(__dirname, 'components'),
    },
  },
  test: {
    globals: true,
    environment: 'node',
  },
})
