import { createRouter, createWebHashHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { noAuth: true },
    },
    {
      path: '/',
      name: 'Home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/jobs',
      name: 'Jobs',
      component: () => import('@/views/JobsView.vue'),
      meta: { title: '岗位介绍' },
    },
    {
      path: '/graph',
      name: 'Graph',
      component: () => import('@/views/GraphView.vue'),
      meta: { title: '岗位图谱' },
    },
    {
      path: '/matching',
      name: 'Matching',
      component: () => import('@/views/MatchingView.vue'),
      meta: { title: '人岗匹配' },
    },
    {
      path: '/user',
      name: 'UserCenter',
      component: () => import('@/views/UserCenterView.vue'),
      meta: { title: '用户中心' },
    },
    {
      path: '/apikey',
      name: 'ApiKey',
      component: () => import('@/views/ApiKeyView.vue'),
      meta: { title: 'API Key 管理', requiresUser: true },
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { title: '数据管理', requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to, _from) => {
  NProgress.start()
  if (!to.meta.noAuth) {
    const token = localStorage.getItem('zc_token')
    if (!token) return '/login'
  }
  if (to.meta.requiresAdmin) {
    const userStore = useUserStore()
    if (!userStore.userInfo) {
      await userStore.init()
    }
    if (userStore.userInfo?.role !== 'admin') {
      return '/'
    }
  }
  if (to.meta.requiresUser) {
    const userStore = useUserStore()
    if (!userStore.userInfo) {
      await userStore.init()
    }
    // token 失效时 init() 会清空 userInfo，必须回落登录页
    if (!userStore.userInfo) return '/login'
    if (userStore.userInfo.role === 'admin') {
      return '/admin' // 管理员走数据管理页
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
