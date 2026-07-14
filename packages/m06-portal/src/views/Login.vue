<template>
  <div class="login-wrapper">
    <!-- 简洁背景，无粒子动画 -->
    <div class="login-bg"></div>

    <div class="login-container">
      <!-- 登录卡片 -->
      <div class="login-card">
        <div class="card-header">
          <div class="logo">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="logo-text">
              <h1>通信基建数智化平台</h1>
            </div>
          </div>
        </div>

        <el-form ref="loginFormRef" :model="form" :rules="rules" class="login-form" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              size="large"
              show-password
              :prefix-icon="Lock"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="login-btn"
              @click="handleLogin"
              :loading="loading"
              size="large"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="card-footer">
          <span class="tips">默认账号：admin &nbsp;/&nbsp; admin123</span>
        </div>
      </div>

      <!-- 右侧：项目简介（替代原来的 feature 卡片） -->
      <div class="login-side">
        <div class="side-header">
          <h2>挑战杯 · 揭榜挂帅</h2>
          <p>XA-202610 通信基建工程数智化设计与交付关键技术</p>
        </div>
        <div class="topic-list">
          <div class="topic-item" v-for="topic in topics" :key="topic.s">
            <span class="topic-s">{{ topic.s }}</span>
            <span class="topic-name">{{ topic.name }}</span>
            <span class="topic-owner">{{ topic.owner }}</span>
          </div>
        </div>
        <div class="side-footer">
          <span>样例区域：山西运城学院</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const loginFormRef = ref(null)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 右侧展示的5个子赛题
const topics = [
  { s: 'S1', name: 'GIS智能辅助设计', owner: '高' },
  { s: 'S2', name: '多源异构数据融合', owner: '任' },
  { s: 'S3', name: '设计智能审查', owner: '王' },
  { s: 'S4', name: '施工指令自动转化', owner: '庞' },
  { s: 'S5', name: '施工过程智能监管', owner: '李' }
]

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    // 开发模式快捷登录
    if (import.meta.env.DEV && form.username === 'admin' && form.password === 'admin123') {
      const testToken = 'test-token-' + Date.now()
      userStore.token = testToken
      localStorage.setItem('token', testToken)
      userStore.userInfo = {
        userId: 1,
        username: 'admin',
        realName: '管理员'
      }
      // 使用与 MainLayout 兜底菜单一致的 S1-S5 赛题命名
      userStore.menus = [
        {
          menuCode: 'design',
          menuName: '智能设计',
          children: [
            { menuCode: 'design_3d', menuName: '三维场景设计' },
            { menuCode: 'design_layout', menuName: '基站布局设计' },
            { menuCode: 'design_coverage', menuName: '覆盖分析' }
          ]
        },
        {
          menuCode: 'fusion',
          menuName: '数据融合',
          children: [
            { menuCode: 'fusion_upload', menuName: 'CAD数据上传' },
            { menuCode: 'fusion_status', menuName: '融合状态' }
          ]
        },
        {
          menuCode: 'review',
          menuName: '智能审查',
          children: [
            { menuCode: 'review_safety', menuName: '安全规范审查' },
            { menuCode: 'review_conflict', menuName: '资源冲突检测' },
            { menuCode: 'review_report', menuName: '审查报告' }
          ]
        },
        {
          menuCode: 'instruction',
          menuName: '施工指令',
          children: [
            { menuCode: 'instruction_bom', menuName: 'BOM生成' },
            { menuCode: 'instruction_process', menuName: '工艺要求' },
            { menuCode: 'instruction_manage', menuName: '施工指令管理' }
          ]
        },
        {
          menuCode: 'supervision',
          menuName: '施工监管',
          children: [
            { menuCode: 'supervision_monitor', menuName: '实时监控' },
            { menuCode: 'supervision_violation', menuName: '违章识别' },
            { menuCode: 'supervision_acceptance', menuName: '验收管理' }
          ]
        },
        {
          menuCode: 'system',
          menuName: '系统管理',
          children: [
            { menuCode: 'system_user', menuName: '用户管理' },
            { menuCode: 'system_role', menuName: '角色管理' }
          ]
        }
      ]
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      await userStore.login(form.username, form.password)
      router.push('/')
    }
  } catch (error) {
    ElMessage.error(error.response?.data || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  position: relative;
  overflow: hidden;
}

/* 用网格线代替粒子动画 —— 工程感 */
.login-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(51, 65, 85, 0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(51, 65, 85, 0.3) 1px, transparent 1px);
  background-size: 48px 48px;
}
.login-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 30% 20%, rgba(37, 99, 235, 0.08) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 80%, rgba(14, 165, 233, 0.06) 0%, transparent 60%);
}

.login-container {
  display: flex;
  gap: 0;
  z-index: 10;
  background: rgba(15, 23, 42, 0.7);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(51, 65, 85, 0.5);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

/* ===== 左侧 登录卡片 ===== */
.login-card {
  width: 380px;
  background: #ffffff;
  padding: 44px 36px 36px;
}

.card-header {
  margin-bottom: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 44px;
  height: 44px;
  background: #1e40af;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.logo-icon svg {
  width: 24px;
  height: 24px;
}

.logo-text h1 {
  font-size: 18px;
  color: #1e293b;
  margin: 0;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.login-form {
  margin-top: 8px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #cbd5e1;
  padding: 4px 12px;
  transition: box-shadow 0.2s;
}

.login-form :deep(.el-input__wrapper:hover),
.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px #2563eb !important;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 8px;
  background: #2563eb;
  border: none;
  transition: all 0.2s;
}

.login-btn:hover {
  background: #1d4ed8;
}

.card-footer {
  margin-top: 20px;
  text-align: center;
}

.tips {
  font-size: 12px;
  color: #94a3b8;
}

/* ===== 右侧 项目简介 ===== */
.login-side {
  width: 300px;
  background: rgba(30, 41, 59, 0.9);
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(51, 65, 85, 0.5);
}

.side-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(71, 85, 105, 0.5);
}

.side-header h2 {
  font-size: 15px;
  color: #e2e8f0;
  margin: 0 0 8px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.side-header p {
  font-size: 11px;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

.topic-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(51, 65, 85, 0.35);
  transition: background 0.2s;
}

.topic-item:hover {
  background: rgba(51, 65, 85, 0.55);
}

.topic-s {
  display: inline-block;
  min-width: 28px;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 0;
  border-radius: 4px;
  line-height: 1.4;
  flex-shrink: 0;
}
.topic-s:nth-child(1) { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
.topic-item:nth-of-type(2) .topic-s { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
.topic-item:nth-of-type(3) .topic-s { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
.topic-item:nth-of-type(4) .topic-s { background: rgba(139, 92, 246, 0.2); color: #c4b5fd; }
.topic-item:nth-of-type(5) .topic-s { background: rgba(236, 72, 153, 0.2); color: #f9a8d4; }

.topic-name {
  font-size: 13px;
  color: #cbd5e1;
  flex: 1;
}

.topic-owner {
  font-size: 12px;
  color: #64748b;
}

.side-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(71, 85, 105, 0.5);
  text-align: center;
}

.side-footer span {
  font-size: 11px;
  color: #475569;
}

/* 响应式 */
@media (max-width: 800px) {
  .login-container {
    flex-direction: column;
    max-width: 400px;
  }

  .login-side {
    width: auto;
    border-left: none;
    border-top: 1px solid rgba(51, 65, 85, 0.5);
    padding: 24px;
  }

  .login-card {
    width: auto;
  }
}
</style>
