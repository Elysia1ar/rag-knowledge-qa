<script setup lang="ts">
import { ref } from 'vue'
import type { SourceItem } from '@/types'

defineProps<{ sources: SourceItem[] }>()

const expanded = ref(false)

// 文件类型 → 图标 + 颜色
const fileTypeMeta: Record<string, { icon: string; color: string }> = {
  pdf:  { icon: 'Document',     color: '#f56c6c' },
  docx: { icon: 'DocumentCopy', color: '#409eff' },
  md:   { icon: 'Document',     color: '#67c23a' },
  txt:  { icon: 'Document',     color: '#909399' },
}

function iconOf(s: SourceItem): string {
  const ft = (s.file_type || '').toLowerCase()
  return fileTypeMeta[ft]?.icon || 'Document'
}

function colorOf(s: SourceItem): string {
  const ft = (s.file_type || '').toLowerCase()
  return fileTypeMeta[ft]?.color || '#909399'
}

/** 生成人类可读的定位信息 */
function locatorOf(s: SourceItem): string {
  if (s.file_type === 'pdf' && typeof s.page === 'number') {
    return `第 ${s.page + 1} 页`
  }
  if (s.heading_path) {
    // 显示最后两级，太长中间省略
    const parts = String(s.heading_path).split(' > ')
    if (parts.length <= 2) return parts.join(' > ')
    return parts.slice(-2).join(' > ')
  }
  return ''
}
</script>

<template>
  <div v-if="sources.length" class="sources">
    <div class="sources-head" @click="expanded = !expanded">
      <el-icon><Document /></el-icon>
      <span>引用来源 · {{ sources.length }} 条</span>
      <el-icon class="arrow" :class="{ up: expanded }"><ArrowDown /></el-icon>
    </div>

    <transition name="el-fade-in">
      <div v-show="expanded" class="sources-body">
        <div
          v-for="s in sources"
          :key="s.chunk_id"
          class="source-item"
        >
          <div class="source-meta">
            <el-tag size="small" type="info" effect="plain">[{{ s.index }}]</el-tag>
            <el-icon class="file-icon" :style="{ color: colorOf(s) }">
              <component :is="iconOf(s)" />
            </el-icon>
            <span class="file">{{ s.file_name }}</span>
            <span v-if="locatorOf(s)" class="locator">{{ locatorOf(s) }}</span>
            <span v-if="s.rerank_score != null" class="score">
              {{ s.rerank_score.toFixed(3) }}
            </span>
          </div>
          <div class="preview">{{ s.preview }}...</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.sources {
  margin-top: 12px;
  background: #f8fafc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.sources-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  user-select: none;
}

.sources-head:hover { background: #eef2f7; }

.arrow { margin-left: auto; transition: transform .2s; }
.arrow.up { transform: rotate(180deg); }

.sources-body {
  border-top: 1px solid #e4e7ed;
  padding: 8px 12px;
}

.source-item { padding: 8px 0; }
.source-item + .source-item { border-top: 1px dashed #e4e7ed; }

.source-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.file-icon { font-size: 13px; }

.file { font-weight: 500; color: #303133; }

.locator {
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.score {
  color: #909399;
  margin-left: auto;
  font-family: monospace;
}

.preview {
  font-size: 12.5px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>