<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { changesApi } from '../api/changes.api'
import { devicesApi } from '@/features/devices/api/devices.api'
import { trackedConceptsApi, severityClassesApi } from '@/features/detection/api/detection.api'
import { useNotificationCounts } from '@/composables/useNotificationCounts'
import type { ConfigChange, ChangeStatus } from '../types'
import type { TrackedConcept, SeverityClass } from '@/features/detection/types'
import type { Device } from '@/features/devices/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { ShieldAlert, CheckCircle2, Info, CheckCheck, ChevronDown, Server } from 'lucide-vue-next'

const props = defineProps<{ id: string }>()
const router = useRouter()
const auth = useAuthStore()
const { refreshCounts } = useNotificationCounts()

const change = ref<ConfigChange | null>(null)
const isLoading = ref(true)
const loadError = ref<string | null>(null)
const ackError = ref<string | null>(null)
const isAcking = ref(false)

const device = ref<Device | null>(null)
const allConcepts = ref<TrackedConcept[]>([])
const allSeverities = ref<SeverityClass[]>([])
const conceptsLoadError = ref(false)

const STATUS_LABELS: Record<ChangeStatus, string> = {
  FLAGGED: 'Flagged',
  INFORMATIONAL: 'Informational',
  ACKNOWLEDGED: 'Acknowledged',
}

async function load() {
  isLoading.value = true
  loadError.value = null
  try {
    change.value = await changesApi.get(props.id)
    if (change.value) {
      devicesApi.get(change.value.device).then((d) => (device.value = d)).catch(() => {})
    }
  } catch {
    loadError.value = 'Could not load this change.'
  } finally {
    isLoading.value = false
  }
}

async function loadConceptData() {
  conceptsLoadError.value = false
  try {
    const [concepts, severities] = await Promise.all([trackedConceptsApi.list(), severityClassesApi.list()])
    allConcepts.value = concepts
    allSeverities.value = severities
  } catch {
    conceptsLoadError.value = true
  }
}

onMounted(() => {
  load()
  loadConceptData()
})

const matchedConcepts = computed(() => {
  if (!change.value) return []
  return change.value.matched_concepts.map((id, i) => {
    const full = allConcepts.value.find((c) => c.id === id)
    return {
      id,
      name: change.value!.matched_concept_names[i] ?? full?.name ?? 'Unknown concept',
      pattern: full?.pattern ?? null,
      severity_class: full?.severity_class ?? null,
    }
  })
})

const severityRankById = computed(() => {
  const map = new Map<number, { name: string; rank: number }>()
  for (const s of allSeverities.value) map.set(s.id, { name: s.name, rank: s.rank })
  return map
})

function severityClass(name: string | null | undefined) {
  const s = name?.toLowerCase()
  if (s === 'high' || s === 'critical') return 'bg-status-critical-bg text-status-critical'
  if (s === 'medium') return 'bg-status-warning-bg text-status-warning'
  if (s === 'low') return 'bg-status-neutral-bg text-status-neutral'
  return 'bg-status-neutral-bg text-status-neutral'
}

function severityBorderClass(name: string | null | undefined) {
  const s = name?.toLowerCase()
  if (s === 'high' || s === 'critical') return 'border-l-status-critical'
  if (s === 'medium') return 'border-l-status-warning'
  if (s === 'low') return 'border-l-status-neutral'
  return 'border-l-border'
}

function statusMeta(status: ChangeStatus) {
  if (status === 'ACKNOWLEDGED') return { class: 'bg-status-healthy-bg text-status-healthy', icon: CheckCircle2 }
  if (status === 'FLAGGED') return { class: 'bg-status-critical-bg text-status-critical', icon: ShieldAlert }
  return { class: 'bg-status-neutral-bg text-status-neutral', icon: Info }
}

async function acknowledge() {
  if (!change.value) return
  ackError.value = null
  isAcking.value = true
  try {
    change.value = await changesApi.acknowledge(change.value.id).then((r) => r.data)
    refreshCounts()
  } catch {
    ackError.value = 'Could not acknowledge this change.'
  } finally {
    isAcking.value = false
  }
}

interface DiffSection {
  id: number
  name: string
  lines: string[]
}

function extractBlockName(headerLine: string | undefined): string | null {
  if (!headerLine) return null
  const m = headerLine.match(/^(?:---|\+\+\+)\s+(?:old|new):\s*(.+)$/)
  return m ? m[1] : null
}

const diffSections = computed<DiffSection[]>(() => {
  if (!change.value?.diff_text) return []
  return change.value.diff_text
    .split('\n\n')
    .filter((raw) => raw.trim().length > 0)
    .map((raw, idx) => {
      const lines = raw.split('\n')
      const oldHeader = lines.find((l) => l.startsWith('--- '))
      const newHeader = lines.find((l) => l.startsWith('+++ '))
      const name = extractBlockName(oldHeader) || extractBlockName(newHeader) || `Change ${idx + 1}`
      const bodyLines = lines.filter((l) => !l.startsWith('--- ') && !l.startsWith('+++ ') && !l.startsWith('@@'))
      return { id: idx, name, lines: bodyLines }
    })
})

const sectionConcepts = computed(() => {
  const map = new Map<number, { name: string; severity_class: number | null }[]>()
  for (const section of diffSections.value) {
    const matches = matchedConcepts.value.filter((c) => {
      if (!c.pattern) return false
      try {
        const regex = new RegExp(c.pattern, 'i')
        // Test against each line individually so ^ and $ work per line!
        return section.lines.some((line) => regex.test(line))
      } catch {
        return false
      }
    })
    map.set(section.id, matches)
  }
  return map
})

function sectionSeverityName(sectionId: number): string | null {
  const concepts = sectionConcepts.value.get(sectionId) ?? []
  let best: { name: string; rank: number } | null = null
  for (const c of concepts) {
    if (c.severity_class == null) continue
    const sev = severityRankById.value.get(c.severity_class)
    if (sev && (!best || sev.rank > best.rank)) best = sev
  }
  return best?.name ?? null
}

function diffLineClass(line: string) {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'bg-status-healthy-bg text-status-healthy'
  if (line.startsWith('-') && !line.startsWith('---')) return 'bg-status-critical-bg text-status-critical'
  return 'text-text-secondary'
}

const sectionRefs = ref<Record<number, HTMLElement | null>>({})
const highlightedSectionId = ref<number | null>(null)
const collapsedSections = ref<Set<number>>(new Set())

function setSectionRef(el: Element | ComponentPublicInstance | null, id: number) {
  sectionRefs.value[id] = el as HTMLElement | null
}

function toggleSection(id: number) {
  if (collapsedSections.value.has(id)) collapsedSections.value.delete(id)
  else collapsedSections.value.add(id)
}

async function scrollToConcept(concept: { pattern: string | null }) {
  if (!concept.pattern) return

  let regex: RegExp

  try {
    regex = new RegExp(concept.pattern, 'i')
  } catch {
    return
  }

  const section = diffSections.value.find((s) =>
    s.lines.some((line) => {
      regex.lastIndex = 0
      return regex.test(line)
    })
  )

  if (!section) return

  collapsedSections.value.delete(section.id)

  await nextTick()

  const el = sectionRefs.value[section.id]

  if (!el) return

  el.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  })

  highlightedSectionId.value = section.id

  window.setTimeout(() => {
    if (highlightedSectionId.value === section.id) {
      highlightedSectionId.value = null
    }
  }, 2500)
}
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <button type="button" class="mb-4 text-sm text-text-secondary hover:text-text-primary cursor-pointer" @click="router.push({ name: 'changes' })">
      ← Back to Changes
    </button>

    <ErrorAlert v-if="loadError" :message="loadError" class="mb-4" />
    <div v-if="isLoading" class="text-sm text-text-secondary">Loading…</div>

    <template v-else-if="change">
      <div class="flex flex-col lg:flex-row gap-6 items-start">
        <!-- Diff — main column with internal scrolling -->
        <div class="flex-1 min-w-0 w-full bg-surface-raised border border-border rounded-lg shadow-sm overflow-hidden flex flex-col lg:max-h-[calc(100vh-140px)]">
          <div class="px-4 py-3 border-b border-border flex items-center justify-between shrink-0 bg-surface-raised">
            <h3 class="text-sm font-medium text-text-secondary">Diff</h3>
            <div class="flex items-center gap-3 text-xs text-text-secondary">
              <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-status-healthy-bg border border-status-healthy"></span> Added</span>
              <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-status-critical-bg border border-status-critical"></span> Removed</span>
            </div>
          </div>

          <div class="overflow-y-auto flex-1">
            <div v-if="!diffSections.length" class="px-4 py-6 text-sm text-text-secondary text-center">
              No differences to show.
            </div>

            <div
              v-for="section in diffSections"
              :key="section.id"
              :ref="(el) => setSectionRef(el, section.id)"
              class="border-b border-border last:border-b-0 border-l-4 transition-all duration-500"
              :class="[
                highlightedSectionId === section.id ? 'border-l-sky-400 bg-sky-500/10 shadow-[inset_4px_0_0_0_#38bdf8]' : severityBorderClass(sectionSeverityName(section.id)),
              ]"
            >
              <button
                type="button"
                class="w-full flex items-center justify-between px-4 py-2.5 bg-surface hover:bg-surface-raised cursor-pointer transition-colors"
                @click="toggleSection(section.id)"
              >
                <span class="flex flex-wrap items-center gap-2 text-sm font-mono text-text-primary">
                  {{ section.name }}
                  <span
                    v-for="c in sectionConcepts.get(section.id) ?? []"
                    :key="c.name"
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="severityClass(severityRankById.get(c.severity_class ?? -1)?.name)"
                  >
                    {{ c.name }}
                  </span>
                </span>
                <ChevronDown class="w-4 h-4 shrink-0 text-text-secondary transition-transform" :class="{ '-rotate-90': collapsedSections.has(section.id) }" />
              </button>

              <pre v-if="!collapsedSections.has(section.id)" class="text-sm font-mono overflow-x-auto py-1"><code
                v-for="(line, idx) in section.lines"
                :key="idx"
                class="block px-4 py-0.5"
                :class="diffLineClass(line)"
              >{{ line }}</code></pre>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="w-full lg:w-80 shrink-0 flex flex-col gap-4 lg:sticky lg:top-4">
          <div class="bg-surface-raised border border-border rounded-lg shadow-sm p-5">
            <div class="flex items-start justify-between mb-3">
              <h2 class="text-lg font-semibold text-text-primary">{{ change.device_name }}</h2>
              <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium" :class="severityClass(change.severity_name)">
                {{ change.severity_name || 'No severity' }}
              </span>
            </div>

            <div v-if="device" class="flex items-center gap-1.5 text-xs text-text-secondary mb-4">
              <Server class="w-3.5 h-3.5" />
              <span>{{ device.management_ip }} · {{ device.device_type }}</span>
            </div>

            <dl class="space-y-3 text-sm">
              <div>
                <dt class="text-text-secondary">Detected</dt>
                <dd class="text-text-primary">{{ new Date(change.detected_at).toLocaleString() }}</dd>
              </div>
              <div>
                <dt class="text-text-secondary">Status</dt>
                <dd>
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" :class="statusMeta(change.status).class">
                    <component :is="statusMeta(change.status).icon" class="w-3 h-3" />
                    {{ STATUS_LABELS[change.status] }}
                  </span>
                </dd>
              </div>
              <div v-if="change.status === 'ACKNOWLEDGED'">
                <dt class="text-text-secondary">Acknowledged</dt>
                <dd class="text-text-primary">
                  {{ change.acknowledged_at ? new Date(change.acknowledged_at).toLocaleString() : '—' }}
                  <span v-if="change.acknowledged_by_username"> by {{ change.acknowledged_by_username }}</span>
                </dd>
              </div>
            </dl>

            <ErrorAlert v-if="ackError" :message="ackError" class="mt-4" />

            <BaseButton
              v-if="change.status === 'FLAGGED' && auth.hasRole('admin', 'operator')"
              class="w-full mt-4"
              title="Mark this change as reviewed"
              :loading="isAcking"
              @click="acknowledge"
            >
              <CheckCheck class="w-4 h-4" />
              {{ isAcking ? 'Acknowledging…' : 'Acknowledge' }}
            </BaseButton>
          </div>

          <div class="bg-surface-raised border border-border rounded-lg shadow-sm p-5">
            <h3 class="text-sm font-medium text-text-secondary mb-3">
              Matched Concepts <span class="text-text-secondary/70 font-normal">({{ matchedConcepts.length }})</span>
            </h3>
            <div v-if="matchedConcepts.length" class="flex flex-wrap gap-2">
              <button
                v-for="concept in matchedConcepts"
                :key="concept.id"
                type="button"
                class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium hover:brightness-110 cursor-pointer transition disabled:cursor-default disabled:opacity-70"
                :class="severityClass(severityRankById.get(concept.severity_class ?? -1)?.name)"
                :disabled="!concept.pattern"
                :title="concept.pattern ? `Jump to where '${concept.name}' matched` : concept.name"
                @click="scrollToConcept(concept)"
              >
                {{ concept.name }}
              </button>
            </div>
            <p v-else class="text-sm text-text-primary">None</p>
            <p v-if="conceptsLoadError" class="text-xs text-amber-600 mt-3">
              Couldn't load concept details — chips are shown without color or jump-to-diff.
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>