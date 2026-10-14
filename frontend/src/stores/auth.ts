import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { login as apiLogin, fetchMe } from '@/api/auth'
import type { LoginRequest } from '@/types'

const TOKEN_KEY = 'rag_token'

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
    const username = ref<string>('')
    const role = ref<'admin' | 'user' | ''>('')
    const initialized = ref(false)

    const isLoggedIn = computed(() => !!token.value)
    const isAdmin = computed(() => role.value === 'admin')

    function setToken(t: string | null) {
        token.value = t
        if (t) localStorage.setItem(TOKEN_KEY, t)
        else localStorage.removeItem(TOKEN_KEY)
    }

    async function login(req: LoginRequest) {
        const res = await apiLogin(req)
        setToken(res.access_token)
        username.value = res.username
        role.value = res.role
        initialized.value = true
    }

    async function loadMe() {
        if (!token.value) {
            initialized.value = true
            return
        }
        try {
            const me = await fetchMe()
            username.value = me.username
            role.value = me.role
        } catch {
            // token 无效，清空
            logout()
        } finally {
            initialized.value = true
        }
    }

    function logout() {
        setToken(null)
        username.value = ''
        role.value = ''
        initialized.value = true
    }

    return {
        token, username, role, initialized,
        isLoggedIn, isAdmin,
        login, loadMe, logout,
    }
})