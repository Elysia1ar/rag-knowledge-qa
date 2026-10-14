/** 文件大小格式化：1234567 → "1.18 MB" */
export function formatSize(bytes: number): string {
    if (!bytes || bytes < 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let i = 0
    let v = bytes
    while (v >= 1024 && i < units.length - 1) {
        v /= 1024
        i++
    }
    return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`
}

/** 时间格式化：ISO 字符串 → "2026-09-15 10:24" */
export function formatTime(iso: string): string {
    if (!iso) return '-'
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const pad = (n: number) => String(n).padStart(2, '0')
    return (
        `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
        `${pad(d.getHours())}:${pad(d.getMinutes())}`
    )
}