import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                // SSE 需要关闭缓冲
                configure: (proxy) => {
                    proxy.on('proxyRes', (proxyRes) => {
                        if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                            proxyRes.headers['cache-control'] = 'no-cache'
                        }
                    })
                },
            },
        },
    },
})
