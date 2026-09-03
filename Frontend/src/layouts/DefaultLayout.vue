<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { useNotificationCounts } from '@/composables/useNotificationCounts'
import UserMenu from '@/components/layout/UserMenu.vue'
import { LayoutDashboard, Server, GitCompareArrows, Bell, ShieldCheck, Users } from 'lucide-vue-next'

const auth = useAuthStore()
const { undeliveredAlerts, flaggedChanges } = useNotificationCounts()

function badgeLabel(n: number): string {
  return n > 9 ? '+9' : String(n)
}

const navItems = computed(() => [
  { to: { name: 'devices' }, label: 'Devices', icon: Server, badge: 0 },
  { to: { name: 'changes' }, label: 'Changes', icon: GitCompareArrows, badge: flaggedChanges.value },
  { to: { name: 'alerts' }, label: 'Alerts', icon: Bell, badge: undeliveredAlerts.value },
])
</script>

<template>
  <div class="min-h-screen flex bg-surface">
    <aside class="w-60 shrink-0 bg-chrome-bg border-r border-chrome-border text-chrome-text p-4 flex flex-col gap-1">
      <h1 class="text-lg font-semibold text-chrome-text-strong mb-6 px-2">ConfigSentinel</h1>

      <nav class="flex flex-col gap-0.5">
        <RouterLink
          :to="{ name: 'dashboard' }"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors hover:bg-chrome-bg-hover hover:text-chrome-text-strong"
          exact-active-class="bg-chrome-bg-active text-brand-600 font-medium"
        >
          <LayoutDashboard class="w-4 h-4 shrink-0" />
          Dashboard
        </RouterLink>

        <RouterLink
          v-for="item in navItems"
          :key="item.label"
          :to="item.to"
          class="flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-chrome-bg-hover hover:text-chrome-text-strong"
          active-class="bg-chrome-bg-active text-brand-600 font-medium"
        >
          <span class="flex items-center gap-2.5">
            <component :is="item.icon" class="w-4 h-4 shrink-0" />
            {{ item.label }}
          </span>
          <span
            v-if="item.badge > 0"
            class="flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-status-critical text-white text-[10px] font-semibold"
          >
            {{ badgeLabel(item.badge) }}
          </span>
        </RouterLink>

        <RouterLink
          v-if="auth.hasRole('admin')"
          :to="{ name: 'detection-profiles' }"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors hover:bg-chrome-bg-hover hover:text-chrome-text-strong"
          active-class="bg-chrome-bg-active text-brand-600 font-medium"
        >
          <ShieldCheck class="w-4 h-4 shrink-0" />
          Detection Profiles
        </RouterLink>
        <RouterLink
          v-if="auth.hasRole('admin')"
          :to="{ name: 'users' }"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors hover:bg-chrome-bg-hover hover:text-chrome-text-strong"
          active-class="bg-chrome-bg-active text-brand-600 font-medium"
        >
          <Users class="w-4 h-4 shrink-0" />
          Users
        </RouterLink>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-14 shrink-0 flex items-center justify-end px-6 border-b border-border bg-surface-raised">
        <UserMenu />
      </header>

      <main class="flex-1 p-6 overflow-y-auto">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>