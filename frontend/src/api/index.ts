import request from './request'
import type { TaskInfo } from '@/types'

export function rebuildIndex(filePath?: string): Promise<TaskInfo> {
    return request.post('/index/rebuild', { file_path: filePath ?? null })
}

export function getTask(taskId: string): Promise<TaskInfo> {
    return request.get(`/index/tasks/${taskId}`)
}

export function listTasks(limit = 10): Promise<TaskInfo[]> {
    return request.get('/index/tasks', { params: { limit } })
}

export function cancelTask(taskId: string): Promise<{ code: number; message: string }> {
    return request.post(`/index/tasks/${taskId}/cancel`)
}