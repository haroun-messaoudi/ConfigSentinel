import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import '@/assets/styles/main.css'

async function init() {
  const app = createApp(App)

  app.use(createPinia())

  const auth = useAuthStore()
  await auth.restoreSession()

  app.use(router)
  app.mount('#app')
}

init()