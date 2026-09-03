import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import type { UserRole } from '@/types'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresGuest?: boolean
    roles?: UserRole[]
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/features/auth/components/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/DefaultLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'devices',
          name: 'devices',
          component: () => import('@/features/devices/components/DeviceListView.vue'),
        },
        {
          path: 'devices/:id',
          name: 'device-detail',
          component: () => import('@/features/devices/components/DeviceDetailView.vue'),
          props: true,
        },
        {
          path: 'changes',
          name: 'changes',
          component: () => import('@/features/changes/components/ChangeListView.vue'),
        },
        {
          path: 'alerts',
          name: 'alerts',
          component: () => import('@/features/alerts/components/AlertListView.vue'),
        },
        {
          path: 'detection-profiles',
          name: 'detection-profiles',
          component: () => import('@/features/detection/components/DetectionProfileListView.vue'),
          meta: { roles: ['admin'] },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/UsersView.vue'),
          meta: { roles: ['admin'] },
        },
        {
          path: 'account/password',
          name: 'change-password',
          component: () => import('@/views/ChangePasswordView.vue'),
        },
        {
          path: 'changes/:id',
          name: 'change-detail',
          component: () => import('@/features/changes/components/ChangeDetailView.vue'),
          props: true,
        },
        {
          path: 'devices/:id/snapshots',
          name: 'device-snapshots',
          component: () => import('@/features/devices/components/DeviceSnapshotsView.vue'),
          props: true,
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 1. Ensure session status is resolved before evaluating navigation
  if (!auth.isReady) {
    await auth.restoreSession()
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const requiresGuest = to.matched.some((record) => record.meta.requiresGuest)

  // 2. Unauthenticated user trying to access protected routes (parent or child)
  if (requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 3. Authenticated user trying to access guest routes (e.g. /login)
  if (requiresGuest && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }

  // 4. Role authorization check
  const requiredRoles = to.meta.roles
  if (requiredRoles && !auth.hasRole(...requiredRoles)) {
    return { name: 'dashboard' }
  }
})

export default router