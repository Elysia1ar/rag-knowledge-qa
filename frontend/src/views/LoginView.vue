<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.login(form)
    ElMessage.success('登录成功')
    router.replace('/chat')
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <div class="brand">
        <div class="brand-mark">R</div>
        <div class="brand-name">RAG 知识库</div>
        <div class="brand-tip">Retrieval-Augmented Generation</div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @submit.prevent="onSubmit"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" clearable>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            show-password
            @keyup.enter="onSubmit"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          style="width: 100%"
          :loading="loading"
          @click="onSubmit"
        >登 录</el-button>
      </el-form>

      <div class="hint">
        默认管理员：admin / admin123
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 380px;
  padding: 40px 36px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.brand { text-align: center; margin-bottom: 28px; }

.brand-mark {
  width: 52px; height: 52px;
  margin: 0 auto 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-name { font-size: 20px; font-weight: 600; color: #1f2d3d; }
.brand-tip { font-size: 12px; color: #909399; margin-top: 4px; }

.hint {
  margin-top: 20px;
  text-align: center;
  font-size: 12px;
  color: #909399;
}
</style>