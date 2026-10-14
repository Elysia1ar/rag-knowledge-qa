import { onBeforeUnmount, ref } from 'vue'
import { getTask } from '@/api/index'
import type { TaskInfo } from '@/types'

/**
 * 轮询任务状态，直到任务结束。
 * 默认每 1 秒轮询一次，任务结束后自动停止。
 */
export function useTaskPolling(intervalMs = 1000) {
    const task = ref<TaskInfo | null>(null)
    const polling = ref(false)
    let timer: number | null = null

    function stop() {
        if (timer !== null) {
            clearInterval(timer)
            timer = null
        }
        polling.value = false
    }

    async function poll(taskId: string) {
        try {
            const info = await getTask(taskId)
            task.value = info
            if (['success', 'failed', 'cancelled'].includes(info.status)) {
                stop()
            }
        } catch {
            stop()
        }
    }

    function start(taskId: string) {
        stop()
        polling.value = true
        // 立即拉一次，避免等 1 秒
        poll(taskId)
        timer = window.setInterval(() => poll(taskId), intervalMs)
    }

    function reset() {
        stop()
        task.value = null
    }

    onBeforeUnmount(stop)

    return { task, polling, start, stop, reset }
}

