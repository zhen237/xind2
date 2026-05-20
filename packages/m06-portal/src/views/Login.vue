<template>
  <div class="login-wrapper">
    <div class="login-bg">
      <div class="particles"></div>
    </div>
    <div class="login-container">
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
              <span>Communication Infrastructure Digital Platform</span>
            </div>
          </div>
        </div>

        <el-form ref="loginFormRef" :model="form" :rules="rules" class="login-form" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <div class="input-wrapper">
              <el-icon class="input-icon"><User /></el-icon>
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                size="large"
                :prefix-icon="User"
              />
            </div>
          </el-form-item>

          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-icon class="input-icon"><Lock /></el-icon>
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                show-password
                @keyup.enter="handleLogin"
              />
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="login-btn"
              @click="handleLogin"
              :loading="loading"
              size="large"
            >
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>
        </el-form>

        <div class="card-footer">
          <div class="tips">
            <el-icon><InfoFilled /></el-icon>
            <span>默认账号: admin / admin123</span>
          </div>
        </div>
      </div>

      <div class="login-features">
        <div class="feature-item" v-for="feature in features" :key="feature.title">
          <div class="feature-icon">
            <el-icon :size="32"><component :is="feature.icon" /></el-icon>
          </div>
          <div class="feature-text">
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { User, Lock, InfoFilled, Monitor, Connection, Box, Bell } from '@element-plus/icons-vue'
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

const features = [
  {
    icon: Monitor,
    title: '数字孪生',
    desc: '实时设备监控与3D可视化'
  },
  {
    icon: Connection,
    title: '智能规划',
    desc: '5G基站智能选址与仿真'
  },
  {
    icon: Box,
    title: 'BIM设计',
    desc: '三维协同设计与碰撞检测'
  },
  {
    icon: Bell,
    title: '智慧运维',
    desc: 'AI告警与智能工单流转'
  }
]

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    if (form.username === 'admin' && form.password === 'admin123') {
      const testToken = 'test-token-' + Date.now()
      userStore.token = testToken
      localStorage.setItem('token', testToken)
      userStore.userInfo = {
        userId: 1,
        username: 'admin',
        realName: '管理员'
      }
      userStore.menus = [
        {
          menuCode: 'system',
          menuName: '系统管理(M01)',
          children: [
            { menuCode: 'system_user', menuName: '用户管理', iframeUrl: null },
            { menuCode: 'system_role', menuName: '角色管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'simulation',
          menuName: '网络规划与仿真(M02)',
          children: [
            { menuCode: 'simulation_plan', menuName: '站点规划', iframeUrl: null },
            { menuCode: 'simulation_analysis', menuName: '覆盖分析', iframeUrl: null }
          ]
        },
        {
          menuCode: 'design',
          menuName: 'BIM+GIS设计(M03)',
          children: [
            { menuCode: 'design_project', menuName: '项目管理', iframeUrl: null },
            { menuCode: 'design_collision', menuName: '碰撞检测', iframeUrl: null }
          ]
        },
        {
          menuCode: 'delivery',
          menuName: '数智化交付(M04)',
          children: [
            { menuCode: 'delivery_doc', menuName: '文档管理', iframeUrl: null },
            { menuCode: 'delivery_order', menuName: '工单管理', iframeUrl: null }
          ]
        },
        {
          menuCode: 'twin',
          menuName: '数字孪生(M05)',
          children: [
            { menuCode: 'twin_monitor', menuName: '实时监控', iframeUrl: null },
            { menuCode: 'twin_alert', menuName: '告警管理', iframeUrl: null }
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
  background: linear-gradient(135deg, #0c1445 0%, #1a365d 50%, #2d3748 100%);
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(14, 165, 233, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 70%);
}

.particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.3), transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.2), transparent),
    radial-gradient(1px 1px at 90px 40px, rgba(255,255,255,0.3), transparent),
    radial-gradient(2px 2px at 130px 80px, rgba(255,255,255,0.2), transparent),
    radial-gradient(1px 1px at 160px 120px, rgba(255,255,255,0.4), transparent);
  background-size: 200px 150px;
  animation: particles 20s linear infinite;
}

@keyframes particles {
  0% { transform: translateY(0); }
  100% { transform: translateY(-150px); }
}

.login-container {
  display: flex;
  gap: 60px;
  align-items: center;
  z-index: 10;
  padding: 20px;
}

.login-card {
  width: 420px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 40px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px rgba(255, 255, 255, 0.1);
}

.card-header {
  margin-bottom: 35px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logo-icon {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

.logo-icon svg {
  width: 28px;
  height: 28px;
}

.logo-text h1 {
  font-size: 20px;
  color: #1a202c;
  margin-bottom: 4px;
  font-weight: 700;
}

.logo-text span {
  font-size: 11px;
  color: #718096;
}

.login-form {
  margin-top: 20px;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.input-wrapper :deep(.el-input__wrapper) {
  padding: 12px 16px 12px 44px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e2e8f0;
  transition: all 0.3s ease;
}

.input-wrapper :deep(.el-input__wrapper:hover),
.input-wrapper :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #667eea, 0 0 20px rgba(102, 126, 234, 0.15);
}

.input-wrapper :deep(.el-input__inner) {
  font-size: 15px;
}

.input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
  color: #a0aec0;
}

.login-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 30px rgba(102, 126, 234, 0.4);
}

.login-btn:active {
  transform: translateY(0);
}

.card-footer {
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.tips {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #718096;
  font-size: 13px;
}

.login-features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  max-width: 400px;
}

.feature-item {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-5px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.feature-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.3));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a78bfa;
  margin-bottom: 16px;
}

.feature-text h3 {
  font-size: 16px;
  color: white;
  margin-bottom: 6px;
  font-weight: 600;
}

.feature-text p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .login-container {
    flex-direction: column;
  }

  .login-features {
    max-width: 420px;
    width: 100%;
  }
}
</style>
