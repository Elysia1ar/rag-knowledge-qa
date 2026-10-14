<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type UploadResult,
} from '@/api/document'
import { rebuildIndex, cancelTask } from '@/api/index'
import { useTaskPolling } from '@/composables/useTaskPolling'
import type { DocumentItem } from '@/types'
import { formatSize, formatTime } from '@/utils/format'
import request from '@/api/request'

const documents = ref<DocumentItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadPercent = ref(0)
const currentFile = ref<string>('')
const search = ref('')
const syncing = ref(false)

const {
  task: rebuildTask,
  start: startPolling,
  stop: stopPolling,
  reset: resetRebuild,
} = useTaskPolling()

function resetRebuildPanel() {
  resetRebuild()
}

const rebuildRunning = computed(() =>
  rebuildTask.value && ['pending', 'running'].includes(rebuildTask.value.status),
)

const filtered = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return documents.value
  return documents.value.filter((d) => d.file_name.toLowerCase().includes(kw))
})

const totalChunks = computed(() =>
  documents.value.reduce((sum, d) => sum + d.chunk_count, 0),
)

async function refresh() {
  loading.value = true
  try {
    documents.value = await listDocuments()
  } finally {
    loading.value = false
  }
}

async function handleUpload(options: any) {
  const rawFile: File = options.file
  if (!rawFile) return

  uploading.value = true
  currentFile.value = rawFile.name
  uploadPercent.value = 0

  try {
    const res: UploadResult = await uploadDocument(rawFile, (p) => {
      uploadPercent.value = p
    })
    if (res.skipped) {
      ElMessage.info(`${rawFile.name} 内容未变，已跳过`)
    } else {
      ElMessage.success(`${rawFile.name} 入库成功，新增 ${res.chunk_count} 个 chunk`)
    }
    await refresh()
    options.onSuccess?.(res)
  } catch (err: any) {
    ElMessage.error(`${rawFile.name} 上传失败：${err?.message || '未知错误'}`)
    options.onError?.(err)
  } finally {
    uploading.value = false
    currentFile.value = ''
    uploadPercent.value = 0
  }
}

async function handleDelete(row: DocumentItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${row.file_name}」吗？此操作会同时从向量库移除其所有 chunk。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteDocument(row.id)
    ElMessage.success('已删除')
    await refresh()
  } catch {
    // 拦截器已提示
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const res: any = await request.post('/documents/sync')
    const { added, updated, missing } = res.data || {}
    ElMessage.success(
      `同步完成：新增 ${added}，更新 ${updated}` +
      (missing > 0 ? `，磁盘缺失 ${missing}` : ''),
    )
    await refresh()
  } finally {
    syncing.value = false
  }
}

async function handleRebuildAll() {
  try {
    await ElMessageBox.confirm(
      '将重新索引所有文档（先删除旧向量再重新写入）。数据量大时可能耗时数分钟。确定继续吗？',
      '全量重建索引',
      { type: 'warning', confirmButtonText: '开始重建', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  try {
    const task = await rebuildIndex()
    ElMessage.success('重建任务已启动')
    startPolling(task.id)
  } catch {
    // 拦截器已提示
  }
}

async function handleCancelRebuild() {
  if (!rebuildTask.value) return
  try {
    await cancelTask(rebuildTask.value.id)
    ElMessage.warning('已请求取消')
  } catch {
    // 拦截器已提示
  }
}

// 任务完成后自动刷新文档列表
import { watch } from 'vue'
watch(
  () => rebuildTask.value?.status,
  (status, prev) => {
    if (status === 'success' && prev !== 'success') {
      ElMessage.success('索引重建完成')
      refresh()
    } else if (status === 'failed') {
      ElMessage.error(`重建失败：${rebuildTask.value?.error || '未知错误'}`)
    } else if (status === 'cancelled') {
      ElMessage.info('重建已取消')
      refresh()
    }
  },
)

onMounted(refresh)
</script>

<template>
  <div class="docs-view">
    <header class="head">
      <div class="head-left">
        <div class="title">文档管理</div>
        <div class="stats">
          共 <b>{{ documents.length }}</b> 篇 ·
          <b>{{ totalChunks }}</b> 个 chunk
        </div>
      </div>
      <div class="head-right">
        <el-input
          v-model="search"
          placeholder="按文件名搜索"
          clearable
          style="width: 180px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button
          :icon="'RefreshRight'"
          @click="handleSync"
          :loading="syncing"
        >同步磁盘</el-button>
        <el-button
          type="primary"
          :icon="'Refresh'"
          @click="handleRebuildAll"
          :disabled="rebuildRunning"
        >重建索引</el-button>
        <el-button :icon="'RefreshLeft'" @click="refresh" :loading="loading">
          刷新
        </el-button>
      </div>
    </header>

    <!-- 重建进度面板 -->
    <transition name="el-fade-in">
      <div v-if="rebuildTask" class="task-panel" :class="rebuildTask.status">
        <div class="task-head">
          <div class="task-title">
            <el-icon>
              <Loading v-if="rebuildRunning" class="spin" />
              <CircleCheck v-else-if="rebuildTask.status === 'success'" />
              <CircleClose v-else-if="rebuildTask.status === 'failed'" />
              <Warning v-else />
            </el-icon>
            <span>{{ rebuildTask.name }}</span>
            <el-tag
              size="small"
              :type="
                rebuildTask.status === 'success' ? 'success' :
                rebuildTask.status === 'failed' ? 'danger' :
                rebuildTask.status === 'cancelled' ? 'warning' : 'primary'
              "
            >
              {{ {
                pending: '等待中',
                running: '运行中',
                success: '完成',
                failed: '失败',
                cancelled: '已取消',
              }[rebuildTask.status] }}
            </el-tag>
          </div>
          <div class="task-actions">
            <el-button
              v-if="rebuildRunning"
              size="small"
              type="warning"
              @click="handleCancelRebuild"
            >取消</el-button>
            <el-button
              v-else
              size="small"
              link
              @click="resetRebuildPanel"
            >关闭</el-button>
          </div>
        </div>

        <el-progress
          :percentage="rebuildTask.progress"
          :status="
            rebuildTask.status === 'failed' ? 'exception' :
            rebuildTask.status === 'success' ? 'success' : undefined
          "
          :stroke-width="8"
        />

        <div class="task-msg">
          <span>{{ rebuildTask.message || '准备中……' }}</span>
          <span class="task-count" v-if="rebuildTask.total > 0">
            {{ rebuildTask.current }} / {{ rebuildTask.total }}
          </span>
        </div>

        <div v-if="rebuildTask.error" class="task-error">
          {{ rebuildTask.error }}
        </div>
      </div>
    </transition>

    <section class="body">
      <div class="upload-area">
        <el-upload
          drag
          multiple
          :show-file-list="false"
          :http-request="handleUpload"
          :disabled="uploading"
          accept=".pdf,.txt,.md,.docx"
        >
          <div class="upload-inner">
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-title">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <div class="upload-tip">
              支持 PDF / TXT / MD / DOCX，可多选
            </div>
          </div>
        </el-upload>

        <transition name="el-fade-in">
          <div v-if="uploading" class="upload-progress">
            <div class="progress-head">
              <span class="progress-file">{{ currentFile }}</span>
              <span class="progress-pct">{{ uploadPercent }}%</span>
            </div>
            <el-progress
              :percentage="uploadPercent"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </transition>
      </div>

      <div class="table-wrap">
        <el-table
          :data="filtered"
          v-loading="loading"
          stripe
          style="width: 100%"
          empty-text="暂无文档，先上传一份吧"
        >
          <el-table-column type="index" width="60" label="#" />
          <el-table-column prop="file_name" label="文件名" min-width="240">
            <template #default="{ row }">
              <div class="file-cell">
                <el-icon class="file-icon"><Document /></el-icon>
                <span>{{ row.file_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="110">
            <template #default="{ row }">
              {{ formatSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column label="Chunk 数" width="110" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.chunk_count }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" width="170">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button
                type="danger"
                link
                size="small"
                @click="handleDelete(row)"
              >删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.docs-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.head {
  padding: 18px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.head-left {
  flex-shrink: 0;       /* 不被右侧挤压 */
  margin-right: 16px;
}
.head-left .title {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;  /* 不换行 */
}

.head-left .stats {
  font-size: 12.5px;
  color: #909399;
  margin-top: 4px;
}
.head-left .stats b { color: #409eff; }

.head-right {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;      /* 窗口窄时按钮换行，而不是挤压标题 */
  justify-content: flex-end;
}

/* 任务面板 */
.task-panel {
  margin: 16px 24px 0;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}
.task-panel.running { border-color: #c6e2ff; background: #f0f9ff; }
.task-panel.success { border-color: #c2e7b0; background: #f0f9eb; }
.task-panel.failed  { border-color: #fbc4c4; background: #fef0f0; }
.task-panel.cancelled { border-color: #faecd8; background: #fdf6ec; }

.task-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.task-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.task-actions { display: flex; gap: 8px; }

.task-msg {
  margin-top: 8px;
  font-size: 12.5px;
  color: #606266;
  display: flex;
  justify-content: space-between;
}
.task-count { font-family: monospace; color: #409eff; }

.task-error {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 6px;
  color: #f56c6c;
  font-size: 12.5px;
}

/* 上传区 */
.body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.upload-area { margin-bottom: 20px; }

.upload-inner {
  padding: 28px 20px;
  text-align: center;
}
.upload-icon {
  font-size: 42px;
  color: #c0c4cc;
  margin-bottom: 10px;
}
.upload-title { font-size: 14px; color: #606266; margin-bottom: 4px; }
.upload-title em { color: #409eff; font-style: normal; font-weight: 500; }
.upload-tip { font-size: 12px; color: #909399; }

.upload-progress {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  color: #606266;
  margin-bottom: 6px;
}
.progress-file { font-weight: 500; }
.progress-pct { font-family: monospace; color: #409eff; }

.table-wrap {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.file-cell { display: flex; align-items: center; gap: 8px; }
.file-icon { color: #409eff; }
</style>