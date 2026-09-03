import { ref } from 'vue'
import { devicesApi } from '../api/devices.api'
import type { Device } from '../types'

const POLL_INTERVAL_MS = 2000
const MAX_POLL_ATTEMPTS = 30 // ~60s before giving up and telling the user

export function useCheckNow() {
  const checkingIds = ref<Set<number>>(new Set())
  const checkErrors = ref<Record<number, string>>({})

  async function checkNow(device: Device, onUpdate: (updated: Device) => void) {
    if (checkingIds.value.has(device.id)) return // already in flight — blocks spamming

    delete checkErrors.value[device.id]
    checkingIds.value.add(device.id)

    const beforeTimestamp = device.last_polled_at

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
        if (updated.last_polled_at && updated.last_polled_at !== beforeTimestamp) {
          onUpdate(updated)
          checkingIds.value.delete(device.id)
          return
        }
      } catch {
        // transient fetch error — keep polling until max attempts rather than
        // failing the whole check on one dropped request
      }

      if (attempts >= MAX_POLL_ATTEMPTS) {
        checkErrors.value[device.id] = 'Check is taking longer than expected. Refresh to see the latest status.'
        checkingIds.value.delete(device.id)
        return
      }

      setTimeout(poll, POLL_INTERVAL_MS)
    }

    setTimeout(poll, POLL_INTERVAL_MS)
  }

  return { checkingIds, checkErrors, checkNow }
}