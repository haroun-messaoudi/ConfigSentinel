import { ref } from 'vue'
import { devicesApi } from '../api/devices.api'
import type { Device } from '../types'
import { useAppNotifications } from '@/composables/useAppNotifications'

const POLL_INTERVAL_MS = 2000
const MAX_POLL_ATTEMPTS = 30 // ~60s before giving up and telling the user

export function useCheckNow() {
  const checkingIds = ref<Set<number>>(new Set())
  const checkErrors = ref<Record<number, string>>({})
  const { notify } = useAppNotifications()

  async function checkNow(device: Device, onUpdate: (updated: Device) => void) {
    if (checkingIds.value.has(device.id)) return // already in flight — blocks spamming

    delete checkErrors.value[device.id]
    checkingIds.value.add(device.id)

    const beforeAttempt = device.last_poll_attempted_at

    try {
      await devicesApi.checkNow(device.id)
    } catch {
      checkErrors.value[device.id] = 'Could not start check.'
      checkingIds.value.delete(device.id)
      return
    }

    let attempts = 0

    const poll = async () => {
      attempts++
      try {
        const updated = await devicesApi.get(device.id)
        if (updated.last_poll_attempted_at && updated.last_poll_attempted_at !== beforeAttempt) {
          onUpdate(updated)
          checkingIds.value.delete(device.id)
          if (updated.last_poll_status === 'ERROR') {
            const message = updated.last_poll_error || 'The device check failed.'
            checkErrors.value[device.id] = message
            notify({
              tone: 'error',
              title: 'Device check failed',
              message: `${device.name}: ${message}`,
            })
          } else {
            delete checkErrors.value[device.id]
          }
          return
        }
      } catch {
        // transient fetch error — keep polling until max attempts rather than
        // failing the whole check on one dropped request
      }

      if (attempts >= MAX_POLL_ATTEMPTS) {
        const message = 'No result was received after 60 seconds. The device may be unreachable, or the backend check worker may not be responding.'
        checkErrors.value[device.id] = message
        checkingIds.value.delete(device.id)
        notify({
          tone: 'error',
          title: 'Device check timed out',
          message: `${device.name}: ${message}`,
        })
        return
      }

      setTimeout(poll, POLL_INTERVAL_MS)
    }

    setTimeout(poll, POLL_INTERVAL_MS)
  }

  return { checkingIds, checkErrors, checkNow }
}