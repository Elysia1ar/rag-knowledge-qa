import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { chatStream } from '@/api/chat'
import { agentChatStream } from '@/api/agent'
import {
    deleteSession as apiDeleteSession,
    getSessionDetail,
    listSessions,
    renameSession as apiRenameSession,
} from '@/api/session'
import type {
    AgentStep,
    ChatMode,
    Message,
    SessionItem,
    SourceItem,
} from '@/types'

let uid = 0
const nextId = () => `m_${Date.now()}_${++uid}`

export const useChatStore = defineStore('chat', () => {
    // ---- 会话相关 ----
    const sessionList = ref<SessionItem[]>([])
    const sessionId = ref<string | null>(null)
    const sessionLoading = ref(false)

    // ---- 对话相关 ----
    const messages = ref<Message[]>([])
    const isLoading = ref(false)
    const mode = ref<ChatMode>('rag')

    let controller: AbortController | null = null

    // ---- 模式 ----
    function setMode(m: ChatMode) {
        if (isLoading.value) return
        mode.value = m
    }

    // ---- 会话列表 ----
    async function loadSessions() {
        try {
            sessionList.value = await listSessions()
        } catch {
            // 拦截器已提示
        }
    }

    // ---- 切换会话 ----
    async function switchSession(id: string) {
        if (isLoading.value) {
            stop()
        }
        if (sessionId.value === id) return

        sessionLoading.value = true
        try {
            const detail = await getSessionDetail(id)
            sessionId.value = detail.id
            messages.value = detail.messages.map((m, i) => {
                let sources: SourceItem[] = []
                try {
                    sources = JSON.parse(m.sources || '[]')
                } catch {
                    sources = []
                }
                return {
                    id: `loaded_${id}_${i}`,
                    role: m.role,
                    content: m.content,
                    sources,
                    status: 'done' as const,
                }
            })
        } finally {
            sessionLoading.value = false
        }
    }

    // ---- 新建会话 ----
    function newSession() {
        if (isLoading.value) stop()
        sessionId.value = null
        messages.value = []
    }

    // ---- 删除会话 ----
    async function removeSession(id: string) {
        await apiDeleteSession(id)
        sessionList.value = sessionList.value.filter((s) => s.id !== id)
        if (sessionId.value === id) {
            newSession()
        }
    }

    // ---- 重命名会话 ----
    async function renameSession(id: string, title: string) {
        const updated = await apiRenameSession(id, title)
        const idx = sessionList.value.findIndex((s) => s.id === id)
        if (idx >= 0) {
            sessionList.value[idx] = updated
        }
    }

    // ---- 发送消息 ----
    async function send(question: string) {
        if (isLoading.value) return
        isLoading.value = true

        messages.value.push({
            id: nextId(),
            role: 'user',
            content: question,
            status: 'done',
        })

        const assistantId = nextId()
        messages.value.push({
            id: assistantId,
            role: 'assistant',
            content: '',
            steps: [],
            mode: mode.value,
            status: 'streaming',
        })

        // 🔑 从数组取出 proxy 引用，否则后续修改不触发响应式
        const assistant = messages.value[messages.value.length - 1]

        controller = new AbortController()

        const handlers = {
            signal: controller.signal,
            onEvent(event: string, data: any) {
                switch (event) {
                    case 'sources':
                        assistant.sources = (data.items || []) as SourceItem[]
                        break

                    case 'action':
                        assistant.steps = assistant.steps || []
                        assistant.steps.push({
                            type: 'action',
                            name: data.name,
                            args: data.args,
                        } as AgentStep)
                        break

                    case 'observation':
                        assistant.steps = assistant.steps || []
                        assistant.steps.push({
                            type: 'observation',
                            content: data.preview,
                        } as AgentStep)
                        break

                    case 'plan':
                        assistant.plan = {
                            goal: data.goal,
                            reasoning: data.reasoning,
                            steps: data.steps,
                        }
                        break

                    case 'step_done':
                        assistant.executions = assistant.executions || []
                        assistant.executions.push({
                            step: data.step,
                            description: data.description,
                            preview: data.preview,
                        })
                        break

                    case 'token':
                        assistant.content += data.text || ''
                        break

                    case 'done':
                        if (data.session_id) {
                            const wasNew = !sessionId.value
                            sessionId.value = data.session_id
                            // 新会话或已有会话：都刷新一次列表
                            if (wasNew) {
                                // 新会话：立刻拉一次以显示自动标题
                                loadSessions()
                            } else {
                                // 已有会话：更新 updated_at
                                loadSessions()
                            }
                        }
                        assistant.status = 'done'
                        break

                    case 'error':
                        assistant.status = 'error'
                        assistant.content += `\n\n[错误] ${data.message || '未知错误'}`
                        break

                    case 'memory':
                        assistant.memoryCount = data.count || 0
                        break
                }
            },
            onError(err: Error) {
                assistant.status = 'error'
                assistant.content = `请求失败：${err.message}`
            },
            onClose() {
                if (assistant.status === 'streaming') {
                    assistant.status = 'done'
                }
                isLoading.value = false
                controller = null
            },
        }

        const req = {
            question,
            session_id: sessionId.value,
            top_k: 5,
            agent_mode: (mode.value === 'plan' ? 'plan' : 'react') as 'react' | 'plan',
        }

        if (mode.value === 'rag') {
            await chatStream(req, handlers)
        } else {
            await agentChatStream(req, handlers)
        }
    }

    function stop() {
        controller?.abort()
        isLoading.value = false
    }

    const currentSessionTitle = computed(() => {
        if (!sessionId.value) return ''
        const s = sessionList.value.find((item) => item.id === sessionId.value)
        return s?.title || ''
    })

    return {
        // 会话
        sessionList,
        sessionId,
        sessionLoading,
        loadSessions,
        switchSession,
        newSession,
        removeSession,
        renameSession,
        currentSessionTitle,
        // 对话
        messages,
        isLoading,
        mode,
        send,
        stop,
        setMode,
    }
})