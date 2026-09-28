import { ref } from 'vue'

export interface AppNotification {
  id: number
  tone: 'success' | 'error'
  title: string
  message: string
}

const notifications = ref<AppNotification[]>([])
const timers = new Map<number, ReturnType<typeof setTimeout>>()
let nextId = 1

function dismiss(id: number) {
  const timer = timers.get(id)
  if (timer) clearTimeout(timer)
  timers.delete(id)
  notifications.value = notifications.value.filter((notification) => notification.id !== id)
}

function notify(notification: Omit<AppNotification, 'id'>) {
  const id = nextId++
  notifications.value.push({ ...notification, id })
  if (notification.tone === 'success') {
    timers.set(id, setTimeout(() => dismiss(id), 8000))
  }
}

export function useAppNotifications() {
  return { notifications, notify, dismiss }
}