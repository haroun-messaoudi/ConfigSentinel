<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import {
  severityClassesApi,
  trackedConceptsApi,
  detectionApi,
} from '../api/detection.api'
import type {
  SeverityClass,
  TrackedConcept,
  DetectionProfile,
} from '../types'
import SeverityClassFormModal from './SeverityClassFormModal.vue'
import TrackedConceptFormModal from './TrackedConceptFormModal.vue'
import DetectionProfileFormModal from './DetectionProfileFormModal.vue'
import {
  Plus,
  Layers,
  Tag,
  ShieldCheck,
  Lock,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'

type Tab = 'severity' | 'concepts' | 'profiles'

const activeTab = ref<Tab>('profiles')

const tabs: {
  id: Tab
  label: string
  icon: typeof ShieldCheck
}[] = [
  {
    id: 'profiles',
    label: 'Detection Profiles',
    icon: ShieldCheck,
  },
  {
    id: 'concepts',
    label: 'Tracked Concepts',
    icon: Tag,
  },
  {
    id: 'severity',
    label: 'Severity Classes',
    icon: Layers,
  },
]

const severityClasses = ref<SeverityClass[]>([])
const trackedConcepts = ref<TrackedConcept[]>([])
const profiles = ref<DetectionProfile[]>([])
const loadError = ref<string | null>(null)
const isLoading = ref(true)

const severityById = computed(() =>
  Object.fromEntries(
    severityClasses.value.map((s) => [s.id, s]),
  ),
)

// ============================================================
// Search & Pagination — Tracked Concepts
// ============================================================

const conceptSearchQuery = ref('')
const conceptCurrentPage = ref(1)
const conceptsPerPage = 10

const filteredTrackedConcepts = computed(() => {
  const query = conceptSearchQuery.value.trim().toLowerCase()

  if (!query) {
    return trackedConcepts.value
  }

  return trackedConcepts.value.filter((concept) => {
    const severityName = concept.severity_class
      ? severityById.value[concept.severity_class]?.name ?? ''
      : ''

    const source =
      concept.source === 'BUILTIN'
        ? 'built-in'
        : 'custom'

    return (
      concept.name.toLowerCase().includes(query) ||
      concept.pattern.toLowerCase().includes(query) ||
      severityName.toLowerCase().includes(query) ||
      source.includes(query)
    )
  })
})

const conceptTotalPages = computed(() => {
  return Math.max(
    1,
    Math.ceil(
      filteredTrackedConcepts.value.length /
        conceptsPerPage,
    ),
  )
})

const paginatedTrackedConcepts = computed(() => {
  const start =
    (conceptCurrentPage.value - 1) *
    conceptsPerPage

  return filteredTrackedConcepts.value.slice(
    start,
    start + conceptsPerPage,
  )
})

const conceptPaginationStart = computed(() => {
  if (filteredTrackedConcepts.value.length === 0) {
    return 0
  }

  return (
    (conceptCurrentPage.value - 1) *
      conceptsPerPage +
    1
  )
})

const conceptPaginationEnd = computed(() => {
  return Math.min(
    conceptCurrentPage.value * conceptsPerPage,
    filteredTrackedConcepts.value.length,
  )
})

const conceptVisiblePages = computed(() => {
  const total = conceptTotalPages.value
  const current = conceptCurrentPage.value

  if (total <= 5) {
    return Array.from(
      { length: total },
      (_, index) => index + 1,
    )
  }

  if (current <= 3) {
    return [1, 2, 3, 4, 5]
  }

  if (current >= total - 2) {
    return [
      total - 4,
      total - 3,
      total - 2,
      total - 1,
      total,
    ]
  }

  return [
    current - 2,
    current - 1,
    current,
    current + 1,
    current + 2,
  ]
})

watch(conceptSearchQuery, () => {
  conceptCurrentPage.value = 1
})

watch(conceptTotalPages, (newTotal) => {
  if (conceptCurrentPage.value > newTotal) {
    conceptCurrentPage.value = newTotal
  }
})

function goToConceptPage(page: number) {
  if (
    page < 1 ||
    page > conceptTotalPages.value
  ) {
    return
  }

  conceptCurrentPage.value = page
}

// ============================================================
// Loading
// ============================================================

async function loadAll() {
  isLoading.value = true
  loadError.value = null

  try {
    const [sev, concepts, profs] =
      await Promise.all([
        severityClassesApi.list(),
        trackedConceptsApi.list(),
        detectionApi.list(),
      ])

    severityClasses.value = sev
    trackedConcepts.value = concepts
    profiles.value = profs
  } catch {
    loadError.value =
      'Could not load detection data. Please try again.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadAll)

// ============================================================
// Severity Classes
// ============================================================

const showSeverityModal = ref(false)
const editingSeverity =
  ref<SeverityClass | null>(null)

const confirmDeleteSeverityId =
  ref<number | null>(null)

const deletingSeverity = ref(false)
const severityDeleteError =
  ref<string | null>(null)

function openCreateSeverity() {
  editingSeverity.value = null
  showSeverityModal.value = true
}

function openEditSeverity(item: SeverityClass) {
  editingSeverity.value = item
  showSeverityModal.value = true
}

function onSeveritySaved(item: SeverityClass) {
  const idx = severityClasses.value.findIndex(
    (s) => s.id === item.id,
  )

  if (idx >= 0) {
    severityClasses.value[idx] = item
  } else {
    severityClasses.value.push(item)
  }
}

async function confirmSeverityDelete(
  id: number,
) {
  deletingSeverity.value = true
  severityDeleteError.value = null

  try {
    await severityClassesApi.remove(id)

    severityClasses.value =
      severityClasses.value.filter(
        (s) => s.id !== id,
      )

    confirmDeleteSeverityId.value = null
  } catch {
    severityDeleteError.value =
      'Could not delete — it may still be in use by a tracked concept.'
  } finally {
    deletingSeverity.value = false
  }
}

// ============================================================
// Tracked Concepts
// ============================================================

const showConceptModal = ref(false)
const editingConcept =
  ref<TrackedConcept | null>(null)

const confirmDeleteConceptId =
  ref<number | null>(null)

const deletingConcept = ref(false)
const conceptDeleteError =
  ref<string | null>(null)

function openCreateConcept() {
  editingConcept.value = null
  showConceptModal.value = true
}

function openEditConcept(
  item: TrackedConcept,
) {
  editingConcept.value = item
  showConceptModal.value = true
}

function onConceptSaved(
  item: TrackedConcept,
) {
  const idx = trackedConcepts.value.findIndex(
    (c) => c.id === item.id,
  )

  if (idx >= 0) {
    trackedConcepts.value[idx] = item
  } else {
    trackedConcepts.value.push(item)
  }

  conceptCurrentPage.value = 1
}

async function confirmConceptDelete(
  id: number,
) {
  deletingConcept.value = true
  conceptDeleteError.value = null

  try {
    await trackedConceptsApi.remove(id)

    trackedConcepts.value =
      trackedConcepts.value.filter(
        (c) => c.id !== id,
      )

    confirmDeleteConceptId.value = null
  } catch {
    conceptDeleteError.value =
      'Could not delete — it may still be in use by a profile.'
  } finally {
    deletingConcept.value = false
  }
}

// ============================================================
// Detection Profiles
// ============================================================

const showProfileModal = ref(false)
const editingProfile =
  ref<DetectionProfile | null>(null)

const confirmDeleteProfileId =
  ref<number | null>(null)

const deletingProfile = ref(false)
const profileDeleteError =
  ref<string | null>(null)

function openCreateProfile() {
  editingProfile.value = null
  showProfileModal.value = true
}

function openEditProfile(
  item: DetectionProfile,
) {
  editingProfile.value = item
  showProfileModal.value = true
}

function onProfileSaved(
  item: DetectionProfile,
) {
  const idx = profiles.value.findIndex(
    (p) => p.id === item.id,
  )

  if (idx >= 0) {
    profiles.value[idx] = item
  } else {
    profiles.value.push(item)
  }
}

async function confirmProfileDelete(
  id: number,
) {
  deletingProfile.value = true
  profileDeleteError.value = null

  try {
    await detectionApi.remove(id)

    profiles.value = profiles.value.filter(
      (p) => p.id !== id,
    )

    confirmDeleteProfileId.value = null
  } catch {
    profileDeleteError.value =
      'Could not delete — it may still be assigned to a device.'
  } finally {
    deletingProfile.value = false
  }
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6">
      <h2
        class="text-xl font-semibold text-text-primary"
      >
        Detection
      </h2>

      <p
        class="text-sm text-text-secondary mt-1"
      >
        Manage severity classes, tracked concepts,
        and detection profiles.
      </p>
    </div>

    <!-- Tabs -->
    <div class="border-b border-border mb-6">
      <nav class="flex gap-6">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="flex items-center gap-1.5 pb-3 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="
            activeTab === tab.id
              ? 'border-brand-500 text-brand-600'
              : 'border-transparent text-text-secondary hover:text-text-primary'
          "
          @click="activeTab = tab.id"
        >
          <component
            :is="tab.icon"
            class="w-4 h-4"
          />

          {{ tab.label }}
        </button>
      </nav>
    </div>

    <ErrorAlert
      v-if="loadError"
      :message="loadError"
      class="mb-4"
    />

    <div
      v-if="isLoading"
      class="text-sm text-text-secondary"
    >
      Loading…
    </div>

    <template v-else>
      <!-- ================================================== -->
      <!-- Detection Profiles -->
      <!-- ================================================== -->

      <div v-show="activeTab === 'profiles'">
        <div class="flex justify-end mb-3">
          <BaseButton
            @click="openCreateProfile"
          >
            <Plus class="w-4 h-4" />
            Add Profile
          </BaseButton>
        </div>

        <ErrorAlert
          v-if="profileDeleteError"
          :message="profileDeleteError"
          class="mb-3"
        />

        <div
          class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm"
        >
          <table class="w-full text-sm">
            <thead
              class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary"
            >
              <tr>
                <th class="px-4 py-3">
                  Name
                </th>

                <th class="px-4 py-3">
                  Tracked Concepts
                </th>

                <th
                  class="px-4 py-3 text-right"
                >
                  Actions
                </th>
              </tr>
            </thead>

            <tbody
              class="divide-y divide-border"
            >
              <tr
                v-for="profile in profiles"
                :key="profile.id"
                class="hover:bg-surface-sunken"
              >
                <td
                  class="px-4 py-3 font-medium text-text-primary"
                >
                  {{ profile.name }}
                </td>

                <td
                  class="px-4 py-3 text-text-secondary"
                >
                  {{
                    profile.tracked_concepts.length
                  }}
                  assigned
                </td>

                <td
                  class="px-4 py-3 text-right"
                >
                  <div
                    v-if="
                      confirmDeleteProfileId ===
                      profile.id
                    "
                    class="flex justify-end items-center gap-2"
                  >
                    <span
                      class="text-xs text-text-secondary"
                    >
                      Delete?
                    </span>

                    <button
                      type="button"
                      class="text-xs font-medium text-status-critical hover:underline disabled:opacity-50"
                      :disabled="deletingProfile"
                      @click="
                        confirmProfileDelete(
                          profile.id,
                        )
                      "
                    >
                      Confirm
                    </button>

                    <button
                      type="button"
                      class="text-xs font-medium text-text-secondary hover:underline"
                      @click="
                        confirmDeleteProfileId =
                          null
                      "
                    >
                      Cancel
                    </button>
                  </div>

                  <div
                    v-else
                    class="flex justify-end gap-2"
                  >
                    <button
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10"
                      @click="
                        openEditProfile(
                          profile,
                        )
                      "
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-status-critical hover:bg-status-critical-bg"
                      @click="
                        confirmDeleteProfileId =
                          profile.id
                      "
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>

              <tr
                v-if="profiles.length === 0"
              >
                <td
                  colspan="3"
                  class="px-4 py-6 text-center text-text-muted"
                >
                  No detection profiles yet.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ================================================== -->
      <!-- Tracked Concepts -->
      <!-- ================================================== -->

      <div v-show="activeTab === 'concepts'">
        <div
          class="flex items-center justify-between gap-4 mb-3"
        >
          <!-- Search -->
          <div
            class="relative w-full max-w-sm"
          >
            <Search
              class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted"
            />

            <input
              v-model="conceptSearchQuery"
              type="text"
              placeholder="Search concepts..."
              class="w-full rounded-md border border-border bg-surface-raised pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
            />
          </div>

          <BaseButton
            @click="openCreateConcept"
          >
            <Plus class="w-4 h-4" />
            Add Concept
          </BaseButton>
        </div>

        <ErrorAlert
          v-if="conceptDeleteError"
          :message="conceptDeleteError"
          class="mb-3"
        />

        <!-- Search has no results -->
        <div
          v-if="
            filteredTrackedConcepts.length ===
            0
          "
          class="bg-surface-raised border border-border rounded-lg p-8 text-center"
        >
          <p
            v-if="trackedConcepts.length === 0"
            class="text-sm text-text-muted"
          >
            No tracked concepts yet.
          </p>

          <p
            v-else
            class="text-sm text-text-secondary"
          >
            No tracked concepts match your search.
          </p>
        </div>

        <!-- Concepts table -->
        <div
          v-else
          class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm"
        >
          <table class="w-full text-sm">
            <thead
              class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary"
            >
              <tr>
                <th class="px-4 py-3">
                  Name
                </th>

                <th class="px-4 py-3">
                  Pattern
                </th>

                <th class="px-4 py-3">
                  Severity
                </th>

                <th class="px-4 py-3">
                  Source
                </th>

                <th
                  class="px-4 py-3 text-right"
                >
                  Actions
                </th>
              </tr>
            </thead>

            <tbody
              class="divide-y divide-border"
            >
              <tr
                v-for="concept in paginatedTrackedConcepts"
                :key="concept.id"
                class="hover:bg-surface-sunken"
              >
                <td
                  class="px-4 py-3 font-medium text-text-primary"
                >
                  {{ concept.name }}
                </td>

                <td
                  class="px-4 py-3 text-text-secondary font-mono text-xs"
                >
                  {{ concept.pattern }}
                </td>

                <td
                  class="px-4 py-3 text-text-secondary"
                >
                  {{
                    concept.severity_class
                      ? severityById[
                          concept.severity_class
                        ]?.name ?? '—'
                      : '—'
                  }}
                </td>

                <td class="px-4 py-3">
                  <span
                    class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="
                      concept.source ===
                      'BUILTIN'
                        ? 'bg-status-neutral-bg text-status-neutral'
                        : 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-600'
                    "
                  >
                    <Lock
                      v-if="
                        concept.source ===
                        'BUILTIN'
                      "
                      class="w-3 h-3"
                    />

                    {{
                      concept.source ===
                      'BUILTIN'
                        ? 'Built-in'
                        : 'Custom'
                    }}
                  </span>
                </td>

                <td
                  class="px-4 py-3 text-right"
                >
                  <div
                    v-if="
                      confirmDeleteConceptId ===
                      concept.id
                    "
                    class="flex justify-end items-center gap-2"
                  >
                    <span
                      class="text-xs text-text-secondary"
                    >
                      Delete?
                    </span>

                    <button
                      type="button"
                      class="text-xs font-medium text-status-critical hover:underline disabled:opacity-50"
                      :disabled="deletingConcept"
                      @click="
                        confirmConceptDelete(
                          concept.id,
                        )
                      "
                    >
                      Confirm
                    </button>

                    <button
                      type="button"
                      class="text-xs font-medium text-text-secondary hover:underline"
                      @click="
                        confirmDeleteConceptId =
                          null
                      "
                    >
                      Cancel
                    </button>
                  </div>

                  <div
                    v-else
                    class="flex justify-end gap-2"
                  >
                    <button
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10"
                      @click="
                        openEditConcept(
                          concept,
                        )
                      "
                    >
                      {{
                        concept.source ===
                        'BUILTIN'
                          ? 'View'
                          : 'Edit'
                      }}
                    </button>

                    <button
                      v-if="
                        concept.source !==
                        'BUILTIN'
                      "
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-status-critical hover:bg-status-critical-bg"
                      @click="
                        confirmDeleteConceptId =
                          concept.id
                      "
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Concepts Pagination -->
          <div
            v-if="conceptTotalPages > 1"
            class="flex items-center justify-between gap-4 border-t border-border px-4 py-3"
          >
            <p
              class="text-xs text-text-secondary"
            >
              Showing
              <span
                class="font-medium text-text-primary"
              >
                {{ conceptPaginationStart }}
              </span>
              –
              <span
                class="font-medium text-text-primary"
              >
                {{ conceptPaginationEnd }}
              </span>
              of
              <span
                class="font-medium text-text-primary"
              >
                {{ filteredTrackedConcepts.length }}
              </span>
            </p>

            <div
              class="flex items-center gap-1"
            >
              <!-- Previous -->
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-md border border-border px-2 py-1.5 text-xs text-text-secondary hover:bg-surface-sunken disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="
                  conceptCurrentPage === 1
                "
                @click="
                  goToConceptPage(
                    conceptCurrentPage - 1,
                  )
                "
              >
                <ChevronLeft
                  class="w-4 h-4"
                />
              </button>

              <!-- Page numbers -->
              <button
                v-for="page in conceptVisiblePages"
                :key="page"
                type="button"
                class="min-w-8 rounded-md px-2 py-1.5 text-xs font-medium transition-colors"
                :class="
                  conceptCurrentPage === page
                    ? 'bg-brand-500 text-white'
                    : 'text-text-secondary hover:bg-surface-sunken'
                "
                @click="
                  goToConceptPage(page)
                "
              >
                {{ page }}
              </button>

              <!-- Next -->
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-md border border-border px-2 py-1.5 text-xs text-text-secondary hover:bg-surface-sunken disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="
                  conceptCurrentPage ===
                  conceptTotalPages
                "
                @click="
                  goToConceptPage(
                    conceptCurrentPage + 1,
                  )
                "
              >
                <ChevronRight
                  class="w-4 h-4"
                />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ================================================== -->
      <!-- Severity Classes -->
      <!-- ================================================== -->

      <div v-show="activeTab === 'severity'">
        <div class="flex justify-end mb-3">
          <BaseButton
            @click="openCreateSeverity"
          >
            <Plus class="w-4 h-4" />
            Add Severity Class
          </BaseButton>
        </div>

        <ErrorAlert
          v-if="severityDeleteError"
          :message="severityDeleteError"
          class="mb-3"
        />

        <div
          class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm"
        >
          <table class="w-full text-sm">
            <thead
              class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary"
            >
              <tr>
                <th class="px-4 py-3">
                  Name
                </th>

                <th class="px-4 py-3">
                  Rank
                </th>

                <th
                  class="px-4 py-3 text-right"
                >
                  Actions
                </th>
              </tr>
            </thead>

            <tbody
              class="divide-y divide-border"
            >
              <tr
                v-for="sev in severityClasses"
                :key="sev.id"
                class="hover:bg-surface-sunken"
              >
                <td
                  class="px-4 py-3 font-medium text-text-primary"
                >
                  {{ sev.name }}
                </td>

                <td
                  class="px-4 py-3 text-text-secondary"
                >
                  {{ sev.rank }}
                </td>

                <td
                  class="px-4 py-3 text-right"
                >
                  <div
                    v-if="
                      confirmDeleteSeverityId ===
                      sev.id
                    "
                    class="flex justify-end items-center gap-2"
                  >
                    <span
                      class="text-xs text-text-secondary"
                    >
                      Delete?
                    </span>

                    <button
                      type="button"
                      class="text-xs font-medium text-status-critical hover:underline disabled:opacity-50"
                      :disabled="deletingSeverity"
                      @click="
                        confirmSeverityDelete(
                          sev.id,
                        )
                      "
                    >
                      Confirm
                    </button>

                    <button
                      type="button"
                      class="text-xs font-medium text-text-secondary hover:underline"
                      @click="
                        confirmDeleteSeverityId =
                          null
                      "
                    >
                      Cancel
                    </button>
                  </div>

                  <div
                    v-else
                    class="flex justify-end gap-2"
                  >
                    <button
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10"
                      @click="
                        openEditSeverity(
                          sev,
                        )
                      "
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      class="rounded px-2 py-1 text-xs font-medium text-status-critical hover:bg-status-critical-bg"
                      @click="
                        confirmDeleteSeverityId =
                          sev.id
                      "
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>

              <tr
                v-if="
                  severityClasses.length ===
                  0
                "
              >
                <td
                  colspan="3"
                  class="px-4 py-6 text-center text-text-muted"
                >
                  No severity classes yet.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Modals -->
    <SeverityClassFormModal
      :open="showSeverityModal"
      :item="editingSeverity"
      @close="showSeverityModal = false"
      @saved="onSeveritySaved"
    />

    <TrackedConceptFormModal
      :open="showConceptModal"
      :item="editingConcept"
      @close="showConceptModal = false"
      @saved="onConceptSaved"
    />

    <DetectionProfileFormModal
      :open="showProfileModal"
      :item="editingProfile"
      @close="showProfileModal = false"
      @saved="onProfileSaved"
    />
  </div>
</template>