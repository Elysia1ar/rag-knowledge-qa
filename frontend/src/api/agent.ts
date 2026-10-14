import { postSSE, type SSEHandlers } from './sse'
import type { ChatRequest } from '@/types'

export function agentChatStream(
    data: ChatRequest,
    handlers: SSEHandlers,
): Promise<void> {
    return postSSE('/api/v1/agent/chat/stream', data, handlers)
}
