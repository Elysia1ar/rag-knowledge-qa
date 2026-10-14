import request from './request'
import type { LoginRequest, LoginResponse, UserInfo } from '@/types'

export function login(data: LoginRequest): Promise<LoginResponse> {
    return request.post('/auth/login', data)
}

export function fetchMe(): Promise<UserInfo> {
    return request.get('/auth/me')
}