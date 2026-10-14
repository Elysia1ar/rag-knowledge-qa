import request from './request'
import type { SessionItem, SessionDetail } from '@/types'

export function listSessions(limit = 50): Promise<SessionItem[]> {
    return request.get('/sessions', { params: { limit } })
}

export function getSessionDetail(id: string): Promise<SessionDetail> {
    return request.get(`/sessions/${id}`)
}

export function renameSession(id: string, title: string): Promise<SessionItem> {
    return request.patch(`/sessions/${id}`, { title })
}

export function deleteSession(id: string): Promise<{ code: number; message: string }> {
    return request.delete(`/sessions/${id}`)
}