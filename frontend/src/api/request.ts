// axios 封装
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
    baseURL: '/api/v1',
    timeout: 60000,
})

// 请求拦截：自动加 token
request.interceptors.request.use((config) => {
    const token = localStorage.getItem('rag_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// 响应拦截：401 跳登录，其他错误弹提示
request.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const status = error.response?.status
        const url: string = error.config?.url || ''

        if (status === 401) {
            // 登录接口自身的 401：显示后端返回的错误信息，不跳转
            if (url.includes('/auth/login')) {
                ElMessage.error(error.response?.data?.detail || '用户名或密码错误')
                return Promise.reject(error)
            }

            // 其他接口的 401：token 失效，清空并跳登录页
            localStorage.removeItem('rag_token')
            if (!location.pathname.includes('/login')) {
                ElMessage.warning('登录已过期，请重新登录')
                location.href = '/login'
            }
            return Promise.reject(error)
        }

        if (status === 403) {
            ElMessage.error(error.response?.data?.detail || '无权限')
            return Promise.reject(error)
        }

        const msg =
            error.response?.data?.detail ||
            error.response?.data?.message ||
            error.message ||
            '请求失败'
        ElMessage.error(msg)
        return Promise.reject(error)
    },
)

export default request