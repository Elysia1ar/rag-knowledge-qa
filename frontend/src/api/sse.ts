//POST + SSE 解析
/**
 * 浏览器原生 EventSource 不支持 POST，这里用 fetch + ReadableStream 手写解析。
 * 后端 SSE 格式：
 *   event: <name>\n
 *   data: <json>\n
 *   \n
 */
export interface SSEHandlers {
    onEvent: (event: string, data: any) => void
    onError?: (err: Error) => void
    onClose?: () => void
    signal?: AbortSignal
}

export async function postSSE(
    url: string,
    body: unknown,
    handlers: SSEHandlers,
): Promise<void> {
    // 原生 fetch 不走 axios 拦截器，这里手动加 Authorization
    const token = localStorage.getItem('rag_token')
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    }
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    let response: Response
    try {
        response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
            signal: handlers.signal,
        })
    } catch (err) {
        handlers.onError?.(err as Error)
        return
    }

    // 401：清 token 并跳登录（和 axios 拦截器行为一致）
    if (response.status === 401) {
        localStorage.removeItem('rag_token')
        if (!location.pathname.includes('/login')) {
            location.href = '/login'
        }
        handlers.onError?.(new Error('登录已过期'))
        return
    }

    if (!response.ok || !response.body) {
        handlers.onError?.(new Error(`SSE 请求失败: HTTP ${response.status}`))
        return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    try {
        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            // stream: true 保证多字节 UTF-8 字符不会被切断
            buffer += decoder.decode(value, { stream: true })

            // 统一换行符：兼容 \r\n（部分代理会转换）
            buffer = buffer.replace(/\r\n/g, '\n')

            let sepIndex: number
            while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
                const rawEvent = buffer.slice(0, sepIndex)
                buffer = buffer.slice(sepIndex + 2)
                if (rawEvent.trim()) {
                    dispatchEvent(rawEvent, handlers.onEvent)
                }
            }
        }

        // 🔑 关键：流结束后 flush 残留 buffer
        // 处理 TCP 分包导致最后一个 \n\n 被切断的情况
        const tail = decoder.decode()
        if (tail) buffer += tail
        if (buffer.trim()) {
            dispatchEvent(buffer, handlers.onEvent)
        }
    } catch (err) {
        if ((err as Error).name !== 'AbortError') {
            handlers.onError?.(err as Error)
        }
    } finally {
        handlers.onClose?.()
    }
}

function dispatchEvent(raw: string, onEvent: (e: string, d: any) => void) {
    console.log('[SSE raw]', JSON.stringify(raw))      // ← 加这行
    let eventName = 'message'
    const dataLines: string[] = []

    for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) {
            eventName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim())
        }
    }

    if (dataLines.length === 0) return
    const dataStr = dataLines.join('\n')

    try {
        onEvent(eventName, JSON.parse(dataStr))
    } catch {
        onEvent(eventName, dataStr)
    }
}