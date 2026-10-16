import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@/services': path.resolve(__dirname, 'src/services'),
      '@/hooks': path.resolve(__dirname, 'src/hooks'),
      '@/types': path.resolve(__dirname, 'src/types'),
      '@/auth': path.resolve(__dirname, 'src/auth'),
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
