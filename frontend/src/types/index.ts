export interface SourceItem {
    index: number
    source: string
    file_name: string
    file_type?: string           // "pdf" | "md" | "docx" | "txt"
    chunk_id: string
    page?: number | null         // PDF 页号（0-based）
    heading_path?: string | null // MD / Word 章节路径
    preview: string
    rerank_score: number | null
}

export interface ChatRequest {
    question: string
    session_id?: string | null
    top_k?: number
    agent_mode?: 'react' | 'plan'           // ← 新增
}

export interface PlanStepInfo {
    step: number
    description: string
    tool: string
}

export interface PlanInfo {
    goal: string
    reasoning?: string
    steps: PlanStepInfo[]
}

export interface PlanExecution {
    step: number
    description: string
    preview: string
}

export interface ChatResponse {
    session_id: string
    question: string
    rewritten_question: string
    answer: string
    sources: SourceItem[]
}

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    sources?: SourceItem[]
    steps?: AgentStep[]          // Agent 模式才有
    plan?: PlanInfo                 // ← 新增
    executions?: PlanExecution[]    // ← 新增
    memoryCount?: number              // ← 新增
    mode?: ChatMode              // 记录该消息来自哪种模式
    status: 'streaming' | 'done' | 'error'
}

export interface DocumentItem {
    id: number
    file_name: string
    file_size: number
    chunk_count: number
    created_at: string
}

export interface LoginRequest {
    username: string
    password: string
}

export interface LoginResponse {
    access_token: string
    token_type: string
    username: string
    role: 'admin' | 'user'
}

export interface UserInfo {
    id: number
    username: string
    role: 'admin' | 'user'
}

export interface VectorStoreStats {
    collection: string
    total_chunks: number
}

export interface DocumentStats {
    total_docs: number
    total_chunks: number
}

export interface SessionStats {
    total_sessions: number
    total_messages: number
}

export interface SystemInfo {
    app_name: string
    app_env: string
    version: string
    embedding_model: string
    embedding_device: string
    reranker_enabled: boolean
    reranker_model: string
    llm_provider: string
    llm_model: string
    chunk_size: number
    chunk_overlap: number
}

export interface StatsResponse {
    vectorstore: VectorStoreStats
    documents: DocumentStats
    sessions: SessionStats
    system: SystemInfo
}

export interface TaskInfo {
    id: string
    name: string
    status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
    progress: number
    current: number
    total: number
    message: string
    error: string | null
    result: Record<string, any> | null
    created_at: string
    updated_at: string
}

export type ChatMode = 'rag' | 'agent' | 'plan'

export interface AgentStep {
    type: 'action' | 'observation'
    name?: string
    args?: Record<string, any>
    content?: string
}

export interface SessionItem {
    id: string
    title: string
    message_count: number
    has_summary?: boolean
    summary_message_count?: number
    created_at: string
    updated_at: string
}

export interface SessionDetail {
    id: string
    title: string
    created_at: string
    updated_at: string
    messages: Array<{
        role: 'user' | 'assistant'
        content: string
        sources: string      // JSON 字符串
    }>
}