import request from './request'
import type { StatsResponse } from '@/types'

export function fetchStats(): Promise<StatsResponse> {
    return request.get('/stats')
}