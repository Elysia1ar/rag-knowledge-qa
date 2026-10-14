<script setup lang="ts">
import { computed } from 'vue'
import type { PlanExecution, PlanInfo } from '@/types'

const props = defineProps<{
  plan: PlanInfo
  executions: PlanExecution[]
  streaming?: boolean
}>()

const stepStatus = computed(() => {
  // step 序号 → "pending" | "running" | "done"
  const execs = props.executions || []
  return props.plan.steps.map((s) => {
    const done = execs.find((e) => e.step === s.step)
    if (done) return 'done'
    // 还没执行到但前面都完成了 → running
    const lastDone = execs.length
    if (s.step === lastDone + 1 && props.streaming) return 'running'
    return 'pending'
  })
})

function executionOf(step: number) {
  return props.executions?.find((e) => e.step === step)
}

const toolLabel: Record<string, string> = {
  search_knowledge: '检索',
  get_current_time: '时间',
  list_documents: '列表',
}
</script>

<template>
  <div class="plan-panel">
    <div class="plan-head">
      <el-icon><Notebook /></el-icon>
      <span>执行计划</span>
      <span class="steps-count">{{ executions.length }} / {{ plan.steps.length }} 完成</span>
    </div>

    <div class="plan-goal">
      <span class="goal-label">目标</span>
      <span class="goal-text">{{ plan.goal }}</span>
    </div>

    <div class="plan-steps">
      <div
        v-for="(s, i) in plan.steps"
        :key="s.step"
        class="plan-step"
        :class="stepStatus[i]"
      >
        <div class="step-index">
          <el-icon v-if="stepStatus[i] === 'done'"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="stepStatus[i] === 'running'" class="spin"><Loading /></el-icon>
          <span v-else>{{ s.step }}</span>
        </div>
        <div class="step-body">
          <div class="step-line">
            <span class="step-desc">{{ s.description }}</span>
            <el-tag size="small" type="info" effect="plain">
              {{ toolLabel[s.tool] || s.tool }}
            </el-tag>
          </div>
          <div v-if="executionOf(s.step)" class="step-preview">
            {{ executionOf(s.step)!.preview.slice(0, 200) }}...
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-panel {
  margin-top: 12px;
  background: #eef6ff;
  border: 1px solid #c6e2ff;
  border-radius: 8px;
  padding: 12px 14px;
}

.plan-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
  margin-bottom: 10px;
}

.steps-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: #60a5fa;
  font-family: monospace;
}

.plan-goal {
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  margin-bottom: 10px;
  font-size: 12.5px;
  display: flex;
  gap: 8px;
}

.goal-label {
  color: #1d4ed8;
  font-weight: 500;
  flex-shrink: 0;
}
.goal-text { color: #303133; }

.plan-steps { display: flex; flex-direction: column; gap: 6px; }

.plan-step {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  transition: all .2s;
}
.plan-step.running { box-shadow: 0 0 0 2px #c6e2ff; }
.plan-step.done { background: #f0f9eb; }

.step-index {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #6b7280;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 600;
}

.plan-step.running .step-index { background: #dbeafe; color: #1d4ed8; }
.plan-step.done .step-index { background: transparent; color: #67c23a; font-size: 20px; }

.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.step-body { flex: 1; min-width: 0; }

.step-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: #303133;
}
.step-desc { flex: 1; }

.step-preview {
  margin-top: 4px;
  font-size: 11.5px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 80px;
  overflow: hidden;
  mask-image: linear-gradient(180deg, #000 70%, transparent);
  -webkit-mask-image: linear-gradient(180deg, #000 70%, transparent);
}
</style>