import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/', redirect: '/chat' },
        {
            path: '/login',
            name: 'login',
            component: () => import('@/views/LoginView.vue'),
            meta: { public: true },
        },
        {
            path: '/chat',
            name: 'chat',
            component: () => import('@/views/ChatView.vue'),
            meta: { title: '智能问答' },
        },
        {
            path: '/documents',
            name: 'documents',
            component: () => import('@/views/DocumentsView.vue'),
            meta: { title: '文档管理', requiresAdmin: true },
        },
        {
            path: '/status',
            name: 'status',
            component: () => import('@/views/StatusView.vue'),
            meta: { title: '系统状态', requiresAdmin: true },
        },
    ],
})

router.beforeEach(async (to) => {
    const auth = useAuthStore()

    // 首次进入，拉一次 /me 确认 token 有效
    if (!auth.initialized) {
        await auth.loadMe()
    }

    // 公开页直接放行
    if (to.meta.public) {
        if (auth.isLoggedIn && to.path === '/login') return '/chat'
        return true
    }

    // 需要登录
    if (!auth.isLoggedIn) {
        return { path: '/login', query: { redirect: to.fullPath } }
    }

    // 需要 admin
    if (to.meta.requiresAdmin && !auth.isAdmin) {
        return '/chat'
    }

    return true
})

export default router