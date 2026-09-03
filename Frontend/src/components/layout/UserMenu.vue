<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { useDarkMode } from '@/composables/useDarkMode'
import { KeyRound, LogOut, Sun, Moon, ChevronDown, User } from 'lucide-vue-next'

const auth = useAuthStore()
const { isDark, toggle } = useDarkMode()

const isOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

function handleClickOutside(event: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div ref="menuRef" class="relative">
    <button
      type="button"
      class="flex items-center gap-2 rounded-md pl-2 pr-2.5 py-1.5 text-sm text-text-primary hover:bg-surface-sunken transition-colors cursor-pointer"
      @click="isOpen = !isOpen"
    >
      <span class="flex items-center justify-center w-7 h-7 rounded-full bg-brand-50 dark:bg-brand-500/10 text-brand-600">
        <User class="w-4 h-4" />
      </span>
      <span class="hidden sm:block text-left">
        <span class="block text-xs font-medium leading-tight truncate max-w-[8rem]">{{ auth.user?.username }}</span>
        <span class="block text-[10px] text-text-secondary leading-tight capitalize">{{ auth.role ?? 'No role' }}</span>
      </span>
      <ChevronDown class="w-3.5 h-3.5 text-text-secondary transition-transform" :class="{ 'rotate-180': isOpen }" />
    </button>

    <Transition name="page">
      <div
        v-if="isOpen"
        class="absolute right-0 mt-1 w-48 rounded-md border border-border bg-surface-raised shadow-lg py-1 z-40"
      >
        <RouterLink
          :to="{ name: 'change-password' }"
          class="flex items-center gap-2.5 px-3 py-2 text-sm text-text-primary hover:bg-surface-sunken transition-colors"
          @click="isOpen = false"
        >
          <KeyRound class="w-4 h-4 text-text-secondary" />
          Change Password
        </RouterLink>

        <button
          type="button"
          class="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-left text-text-primary hover:bg-surface-sunken transition-colors cursor-pointer"
          @click="toggle"
        >
          <component :is="isDark ? Sun : Moon" class="w-4 h-4 text-text-secondary" />
          {{ isDark ? 'Light Mode' : 'Dark Mode' }}
        </button>

        <div class="border-t border-border my-1" />

        <button
          type="button"
          class="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-left text-status-critical hover:bg-status-critical-bg transition-colors cursor-pointer"
          @click="auth.logout()"
        >
          <LogOut class="w-4 h-4" />
          Log out
        </button>
      </div>
    </Transition>
  </div>
</template>