import request from './request'
import type { DocumentItem } from '@/types'

export interface UploadResult {
    document_id: number
    file_name: string
    chunk_count: number
    skipped: boolean
}

export function listDocuments(): Promise<DocumentItem[]> {
    return request.get('/documents')
}

export function uploadDocument(
    file: File,
    onProgress?: (percent: number) => void,
): Promise<UploadResult> {
    const form = new FormData()
    form.append('file', file)
    return request.post('/documents', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
            if (e.total && onProgress) {
                onProgress(Math.round((e.loaded / e.total) * 100))
            }
        },
    })
}

export function deleteDocument(id: number) {
    return request.delete(`/documents/${id}`)
}