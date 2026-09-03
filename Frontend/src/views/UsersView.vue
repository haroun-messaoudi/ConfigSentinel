<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { usersApi } from '@/features/users/api/users.api'
import type { AppUser, UserFormPayload } from '@/features/users/types'
import type { ApiError } from '@/types'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { ShieldCheck, Wrench, Eye, UserPlus } from 'lucide-vue-next'

const ROLE_OPTIONS = [
  { value: 'Admin', label: 'Admin' },
  { value: 'Operator', label: 'Operator' },
  { value: 'Viewer', label: 'Viewer' },
]

const ROLE_ICON: Record<string, typeof ShieldCheck> = {
  Admin: ShieldCheck,
  Operator: Wrench,
  Viewer: Eye,
}

const users = ref<AppUser[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)

const showModal = ref(false)
const saving = ref(false)
const submitError = ref<string | null>(null)

const form = reactive<UserFormPayload>({
  username: '',
  email: '',
  role: null,
  password: '',
  is_active: true,
})

const confirmPassword = ref('')
const fieldErrors = reactive<Record<string, string>>({})

const showEditModal = ref(false)
const editingUserId = ref<number | null>(null)
const editSaving = ref(false)
const editSubmitError = ref<string | null>(null)
const editFieldErrors = reactive<Record<string, string>>({})
const editForm = reactive<{
  username: string
  email: string
  role: string | null
}>({
  username: '',
  email: '',
  role: null,
})

/*
 * Activate / Deactivate confirmation
 */
const showStatusConfirmModal = ref(false)
const statusConfirmUser = ref<AppUser | null>(null)
const statusConfirmSaving = ref(false)

async function fetchUsers() {
  loading.value = true
  loadError.value = null

  try {
    users.value = await usersApi.list()
  } catch (e) {
    loadError.value = (e as ApiError).message
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)

function lastActiveLabel(user: AppUser): string {
  if (!user.last_login) return 'Never logged in'

  const diffMs = Date.now() - new Date(user.last_login).getTime()
  const mins = Math.floor(diffMs / 60000)

  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`

  const hours = Math.floor(mins / 60)

  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function openCreateModal() {
  form.username = ''
  form.email = ''
  form.role = null
  form.password = ''
  form.is_active = true

  confirmPassword.value = ''

  Object.keys(fieldErrors).forEach((k) => delete fieldErrors[k])

  submitError.value = null
  showModal.value = true
}

function validate(): boolean {
  Object.keys(fieldErrors).forEach((k) => delete fieldErrors[k])

  if (!form.username.trim()) {
    fieldErrors.username = 'Username is required.'
  } else if (form.username.length < 3) {
    fieldErrors.username = 'Must be at least 3 characters.'
  }

  if (!form.email.trim()) {
    fieldErrors.email = 'Email is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    fieldErrors.email = 'Enter a valid email address.'
  }

  if (!form.password) {
    fieldErrors.password = 'Password is required.'
  } else if (form.password.length < 8) {
    fieldErrors.password = 'Password must be at least 8 characters.'
  }

  if (form.password && confirmPassword.value !== form.password) {
    fieldErrors.confirmPassword = 'Passwords do not match.'
  }

  return Object.keys(fieldErrors).length === 0
}

async function submitForm() {
  submitError.value = null

  if (!validate()) return

  saving.value = true

  try {
    const { data } = await usersApi.create(form)

    users.value = [data, ...users.value]
    showModal.value = false
  } catch (e) {
    const err = e as ApiError

    if (err.fieldErrors) {
      for (const [key, msgs] of Object.entries(err.fieldErrors)) {
        fieldErrors[key] = msgs[0]
      }
    } else {
      submitError.value = err.message
    }
  } finally {
    saving.value = false
  }
}

/*
 * Open confirmation before changing user status.
 */
function requestToggleActive(user: AppUser) {
  statusConfirmUser.value = user
  showStatusConfirmModal.value = true
}

/*
 * Actually perform the activation/deactivation only after
 * the administrator confirms.
 */
async function confirmToggleActive() {
  if (!statusConfirmUser.value) return

  const user = statusConfirmUser.value
  const newStatus = !user.is_active

  statusConfirmSaving.value = true

  try {
    const { data } = await usersApi.update(user.id, {
      is_active: newStatus,
    })

    const index = users.value.findIndex((u) => u.id === data.id)

    if (index >= 0) {
      users.value[index] = data
    }

    showStatusConfirmModal.value = false
    statusConfirmUser.value = null
  } catch {
    // The user list remains unchanged if the request fails.
  } finally {
    statusConfirmSaving.value = false
  }
}

function cancelToggleActive() {
  if (statusConfirmSaving.value) return

  showStatusConfirmModal.value = false
  statusConfirmUser.value = null
}

function openEditModal(user: AppUser) {
  editingUserId.value = user.id
  editForm.username = user.username
  editForm.email = user.email
  editForm.role = user.role

  Object.keys(editFieldErrors).forEach((k) => delete editFieldErrors[k])

  editSubmitError.value = null
  showEditModal.value = true
}

function validateEdit(): boolean {
  Object.keys(editFieldErrors).forEach((k) => delete editFieldErrors[k])

  if (!editForm.username.trim()) {
    editFieldErrors.username = 'Username is required.'
  } else if (editForm.username.length < 3) {
    editFieldErrors.username = 'Must be at least 3 characters.'
  }

  if (!editForm.email.trim()) {
    editFieldErrors.email = 'Email is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editForm.email)) {
    editFieldErrors.email = 'Enter a valid email address.'
  }

  return Object.keys(editFieldErrors).length === 0
}

async function submitEditForm() {
  editSubmitError.value = null

  if (!validateEdit() || editingUserId.value === null) return

  editSaving.value = true

  try {
    const { data } = await usersApi.update(editingUserId.value, {
      username: editForm.username,
      email: editForm.email,
      role: editForm.role,
    })

    const idx = users.value.findIndex((u) => u.id === data.id)

    if (idx >= 0) {
      users.value[idx] = data
    }

    showEditModal.value = false
  } catch (e) {
    const err = e as ApiError

    if (err.fieldErrors) {
      for (const [key, msgs] of Object.entries(err.fieldErrors)) {
        editFieldErrors[key] = msgs[0]
      }
    } else {
      editSubmitError.value = err.message
    }
  } finally {
    editSaving.value = false
  }
}

const activeCount = computed(() => {
  return users.value.filter((u) => u.is_active).length
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-semibold text-text-primary">
          Users
        </h2>

        <p class="text-sm text-text-secondary mt-1">
          {{ activeCount }} active of {{ users.length }} total
        </p>
      </div>

      <BaseButton @click="openCreateModal">
        <UserPlus class="w-4 h-4" />
        New User
      </BaseButton>
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="text-sm text-text-secondary"
    >
      Loading users…
    </div>

    <!-- Error -->
    <ErrorAlert
      v-else-if="loadError"
      :message="loadError"
    />

    <!-- Empty -->
    <div
      v-else-if="users.length === 0"
      class="rounded-lg border border-border bg-surface-raised p-6 text-sm text-text-secondary"
    >
      No users yet. Create the first one.
    </div>

    <!-- Users table -->
    <div
      v-else
      class="rounded-lg border border-border bg-surface-raised overflow-hidden"
    >
      <table class="w-full text-sm">
        <thead
          class="bg-surface-sunken text-text-secondary text-left"
        >
          <tr>
            <th class="px-4 py-3 font-medium">
              User
            </th>

            <th class="px-4 py-3 font-medium">
              Role
            </th>

            <th class="px-4 py-3 font-medium">
              Status
            </th>

            <th class="px-4 py-3 font-medium">
              Last active
            </th>

            <th class="px-4 py-3 font-medium"></th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="user in users"
            :key="user.id"
            class="border-t border-border"
          >
            <!-- User -->
            <td class="px-4 py-3">
              <div class="text-text-primary font-medium">
                {{ user.username }}
              </div>

              <div class="text-text-muted text-xs">
                {{ user.email }}
              </div>
            </td>

            <!-- Role -->
            <td class="px-4 py-3">
              <span
                v-if="user.role"
                class="inline-flex items-center gap-1.5 text-text-secondary"
              >
                <component
                  :is="ROLE_ICON[user.role]"
                  class="w-3.5 h-3.5"
                />

                {{ user.role }}
              </span>

              <span
                v-else
                class="text-text-muted"
              >
                —
              </span>
            </td>

            <!-- Status -->
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                :class="
                  user.is_active
                    ? 'bg-status-healthy-bg text-status-healthy'
                    : 'bg-status-neutral-bg text-status-neutral'
                "
              >
                {{ user.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>

            <!-- Last active -->
            <td class="px-4 py-3 text-text-secondary">
              {{ lastActiveLabel(user) }}
            </td>

            <!-- Actions -->
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end gap-3">
                <button
                  class="text-xs text-brand-600 hover:text-brand-700 font-medium"
                  @click="openEditModal(user)"
                >
                  Edit
                </button>

                <button
                  class="text-xs text-text-secondary hover:text-text-primary font-medium"
                  @click="requestToggleActive(user)"
                >
                  {{ user.is_active ? 'Deactivate' : 'Activate' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <BaseModal
      :open="showModal"
      title="New User"
      @close="showModal = false"
    >
      <ErrorAlert
        v-if="submitError"
        :message="submitError"
        class="mb-4"
      />

      <form
        class="space-y-4"
        @submit.prevent="submitForm"
      >
        <BaseInput
          id="new-username"
          v-model="form.username"
          label="Username"
          :error="fieldErrors.username"
          :disabled="saving"
        />

        <BaseInput
          id="new-email"
          v-model="form.email"
          label="Email"
          type="email"
          :error="fieldErrors.email"
          :disabled="saving"
        />

        <BaseSelect
          id="new-role"
          v-model="form.role as string"
          label="Role"
          placeholder="No role"
          :options="ROLE_OPTIONS"
          :disabled="saving"
        />

        <BaseInput
          id="new-password"
          v-model="form.password"
          label="Password"
          type="password"
          :error="fieldErrors.password"
          :disabled="saving"
        />

        <BaseInput
          id="new-confirm-password"
          v-model="confirmPassword"
          label="Confirm password"
          type="password"
          :error="fieldErrors.confirmPassword"
          :disabled="saving"
        />

        <div class="flex justify-end gap-2 pt-2">
          <BaseButton
            type="button"
            variant="secondary"
            :disabled="saving"
            @click="showModal = false"
          >
            Cancel
          </BaseButton>

          <BaseButton
            type="submit"
            :loading="saving"
          >
            {{ saving ? 'Creating…' : 'Create user' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <!-- Edit modal -->
    <BaseModal
      :open="showEditModal"
      title="Edit User"
      @close="showEditModal = false"
    >
      <ErrorAlert
        v-if="editSubmitError"
        :message="editSubmitError"
        class="mb-4"
      />

      <form
        class="space-y-4"
        @submit.prevent="submitEditForm"
      >
        <BaseInput
          id="edit-username"
          v-model="editForm.username"
          label="Username"
          :error="editFieldErrors.username"
          :disabled="editSaving"
        />

        <BaseInput
          id="edit-email"
          v-model="editForm.email"
          label="Email"
          type="email"
          :error="editFieldErrors.email"
          :disabled="editSaving"
        />

        <BaseSelect
          id="edit-role"
          v-model="editForm.role as string"
          label="Role"
          placeholder="No role"
          :options="ROLE_OPTIONS"
          :disabled="editSaving"
        />

        <p class="text-xs text-text-muted">
          Password changes are handled by the user themselves via
          their account settings.
        </p>

        <div class="flex justify-end gap-2 pt-2">
          <BaseButton
            type="button"
            variant="secondary"
            :disabled="editSaving"
            @click="showEditModal = false"
          >
            Cancel
          </BaseButton>

          <BaseButton
            type="submit"
            :loading="editSaving"
          >
            {{ editSaving ? 'Saving…' : 'Save changes' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <!-- Activate / Deactivate confirmation modal -->
    <BaseModal
      :open="showStatusConfirmModal"
      :title="
        statusConfirmUser?.is_active
          ? 'Deactivate user?'
          : 'Activate user?'
      "
      @close="cancelToggleActive"
    >
      <div
        v-if="statusConfirmUser"
        class="space-y-4"
      >
        <!-- Warning message -->
        <div>
          <p class="text-sm text-text-secondary">
            Are you sure you want to
            <strong class="text-text-primary">
              {{
                statusConfirmUser.is_active
                  ? 'deactivate'
                  : 'activate'
              }}
            </strong>
            the account
            <strong class="text-text-primary">
              {{ statusConfirmUser.username }}
            </strong>?
          </p>
        </div>

        <!-- Warning box -->
        <div
          class="rounded-lg border border-status-warning bg-status-warning-bg p-3"
        >
          <p class="text-sm font-medium text-status-warning">
            {{
              statusConfirmUser.is_active
                ? 'This user will lose access to ConfigGuard.'
                : 'This user will regain access to ConfigGuard.'
            }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2 pt-2">
          <BaseButton
            type="button"
            variant="secondary"
            :disabled="statusConfirmSaving"
            @click="cancelToggleActive"
          >
            Cancel
          </BaseButton>

          <BaseButton
            type="button"
            :loading="statusConfirmSaving"
            @click="confirmToggleActive"
          >
            {{
              statusConfirmSaving
                ? 'Updating…'
                : statusConfirmUser.is_active
                  ? 'Deactivate user'
                  : 'Activate user'
            }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>