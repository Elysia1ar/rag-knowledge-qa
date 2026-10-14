<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchStats } from '@/api/stats'
import type { StatsResponse } from '@/types'

const stats = ref<StatsResponse | null>(null)
const loading = ref(false)
const healthy = ref<boolean | null>(null)
const lastUpdated = ref<string>('')

async function refresh() {
  loading.value = true
  try {
    stats.value = await fetchStats()
    healthy.value = true
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
  } catch {
    healthy.value = false
  } finally {
    loading.value = false
  }
}

onMounted(refresh)

const cards = computed(() => {
  if (!stats.value) return []
  const { vectorstore, documents, sessions } = stats.value
  return [
    {
      label: '知识库文档',
      value: documents.total_docs,
      suffix: '篇',
      icon: 'Document',
      color: '#409eff',
    },
    {
      label: '向量 Chunk',
      value: vectorstore.total_chunks,
      suffix: '个',
      icon: 'Grid',
      color: '#67c23a',
    },
    {
      label: '会话总数',
      value: sessions.total_sessions,
      suffix: '个',
      icon: 'ChatDotSquare',
      color: '#e6a23c',
    },
    {
      label: '消息总数',
      value: sessions.total_messages,
      suffix: '条',
      icon: 'ChatLineSquare',
      color: '#8b5cf6',
    },
  ]
})

const systemRows = computed(() => {
  if (!stats.value) return []
  const s = stats.value.system
  return [
    { key: '应用名称', value: s.app_name },
    { key: '版本', value: `v${s.version}` },
    { key: '运行环境', value: s.app_env },
    { key: 'Embedding 模型', value: s.embedding_model },
    { key: 'Embedding 设备', value: s.embedding_device },
    {
      key: 'Reranker',
      value: s.reranker_enabled ? `${s.reranker_model}（已启用）` : '未启用',
    },
    { key: 'LLM 供应商', value: s.llm_provider },
    { key: 'LLM 模型', value: s.llm_model },
    { key: '分块大小', value: `${s.chunk_size} 字符（重叠 ${s.chunk_overlap}）` },
    { key: '向量集合', value: stats.value.vectorstore.collection },
  ]
})
</script>

<template>
  <div class="status-view">
    <header class="head">
      <div class="head-left">
        <div class="title">系统状态</div>
        <div class="sub">
          最后更新：{{ lastUpdated || '-' }}
        </div>
      </div>
      <div class="head-right">
        <el-tag v-if="healthy === true" type="success" effect="light">
          <el-icon><CircleCheck /></el-icon> 服务正常
        </el-tag>
        <el-tag v-else-if="healthy === false" type="danger" effect="light">
          <el-icon><CircleClose /></el-icon> 连接失败
        </el-tag>
        <el-button :icon="'Refresh'" @click="refresh" :loading="loading">
          刷新
        </el-button>
      </div>
    </header>

    <section class="body" v-loading="loading">
      <!-- 统计卡片 -->
      <div class="cards">
        <div
          v-for="c in cards"
          :key="c.label"
          class="card"
        >
          <div class="card-icon" :style="{ background: c.color }">
            <el-icon><component :is="c.icon" /></el-icon>
          </div>
          <div class="card-content">
            <div class="card-value">
              {{ c.value }}<span class="suffix">{{ c.suffix }}</span>
            </div>
            <div class="card-label">{{ c.label }}</div>
          </div>
        </div>
      </div>

      <!-- 系统信息 -->
      <div class="panel">
        <div class="panel-title">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item
            v-for="row in systemRows"
            :key="row.key"
            :label="row.key"
          >
            <span class="mono">{{ row.value }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </section>
  </div>
</template>

<style scoped>
.status-view {
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

.head-left .title { font-size: 16px; font-weight: 600; }
.head-left .sub { font-size: 12.5px; color: #909399; margin-top: 4px; }

.head-right { display: flex; gap: 12px; align-items: center; }

.body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all .2s;
}
.card:hover {
  border-color: #c0e0ff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.08);
  transform: translateY(-1px);
}

.card-icon {
  width: 48px; height: 48px;
  border-radius: 10px;
  color: #fff;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-value {
  font-size: 26px;
  font-weight: 600;
  color: #1f2d3d;
  line-height: 1.2;
}
.card-value .suffix {
  font-size: 13px;
  color: #909399;
  font-weight: 400;
  margin-left: 4px;
}

.card-label {
  font-size: 13px;
  color: #606266;
  margin-top: 4px;
}

.panel {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 20px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12.5px;
  color: #303133;
}
</style>