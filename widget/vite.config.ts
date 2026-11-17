import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: mode === 'production' ? {
    'process.env.NODE_ENV': JSON.stringify('production'),
  } : {},
  build: {
    lib: {
      entry: 'src/index.tsx',
      name: 'SupportWidget',
      formats: ['iife'],
      fileName: () => 'widget.js',
    },
    rollupOptions: {
      output: {
        extend: true,
        inlineDynamicImports: true,
      },
    },
    minify: 'esbuild',
    target: 'es2020',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
  },
}));
