import request from './request'
import { postSSE, type SSEHandlers } from './sse'
import type { ChatRequest, ChatResponse } from '@/types'

export function chatSync(data: ChatRequest): Promise<ChatResponse> {
    return request.post('/chat', data)
}

export function chatStream(
    data: ChatRequest,
    handlers: SSEHandlers,
): Promise<void> {
    return postSSE('/api/v1/chat/stream', data, handlers)
}

export function getSession(sessionId: string) {
    return request.get(`/sessions/${sessionId}`)
}