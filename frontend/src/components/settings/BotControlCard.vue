<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useAuthStore } from '@/stores/auth.store'
import { useConfigStore } from '@/stores/config.store'

const authStore   = useAuthStore()
const configStore = useConfigStore()
const confirm     = useConfirm()

// Estado del engine
const isRunning  = ref(true)
const isPaused   = ref(false)
const isLoading  = ref(false)
const loadError  = ref<string | null>(null)

// El bot está "activo" cuando corre y NO está pausado
const isActive = computed(() => isRunning.value && !isPaused.value)
const isMock   = computed(() => configStore.config.mockModeEnabled)

const statusLabel = computed(() => {
  if (!isRunning.value) return 'Motor detenido'
  if (isPaused.value)   return isMock.value ? 'En pausa (Modo Demo)' : 'En pausa'
  return isMock.value ? 'Operando (Modo Demo)' : 'Operando'
})

const statusSeverity = computed(() =>
  isActive.value ? (isMock.value ? 'warn' : 'success') : 'secondary'
)

async function fetchStatus(): Promise<void> {
  try {
    const res = await authStore.fetchWithAuth('/api/engine')
    if (res.ok) {
      const data = await res.json() as { is_running: boolean; is_paused: boolean }
      isRunning.value = data.is_running
      isPaused.value  = data.is_paused
    }
  } catch {
    loadError.value = 'No se pudo obtener el estado del motor'
  }
}

function onToggleRequest(): void {
  const willPause = isActive.value

  confirm.require({
    group: 'bot-control',
    header: willPause ? 'Detener operaciones' : 'Iniciar operaciones',
    message: willPause
      ? 'El motor dejará de procesar oportunidades de arbitraje. Los feeds de mercado seguirán activos. ¿Continuar?'
      : 'El motor comenzará a detectar y simular oportunidades de arbitraje. ¿Continuar?',
    icon: willPause ? 'pi pi-pause' : 'pi pi-play',
    acceptLabel: willPause ? 'Detener' : 'Iniciar',
    rejectLabel: 'Cancelar',
    accept: () => applyToggle(willPause),
  })
}

async function applyToggle(willPause: boolean): Promise<void> {
  isLoading.value = true
  try {
    const res = await authStore.fetchWithAuth('/api/engine', {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ paused: willPause }),
    })
    if (res.ok) {
      const data = await res.json() as { is_running: boolean; is_paused: boolean }
      isRunning.value = data.is_running
      isPaused.value  = data.is_paused
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchStatus)
</script>

<template>
  <section class="settings-section bot-control-section">
    <div class="bot-control-header">
      <h2 class="settings-section-title">Control del Motor</h2>
      <Tag :value="statusLabel" :severity="statusSeverity" class="bot-status-tag" />
    </div>

    <p class="settings-section-desc">
      Inicia o detiene el procesamiento de oportunidades de arbitraje.
      Al detener, los feeds de mercado permanecen activos — el motor
      retoma inmediatamente al reanudar, sin necesidad de reiniciar.
    </p>

    <div v-if="loadError" class="bot-error">{{ loadError }}</div>

    <div class="bot-control-action">
      <Button
        :label="isActive ? 'Detener operaciones' : 'Iniciar a operar'"
        :icon="isActive ? 'pi pi-pause' : 'pi pi-play'"
        :severity="isActive ? 'danger' : 'success'"
        :loading="isLoading"
        :disabled="isLoading || !isRunning"
        outlined
        @click="onToggleRequest"
      />
    </div>

    <ConfirmDialog group="bot-control" />
  </section>
</template>

<style scoped>
.bot-control-section {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bot-control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.settings-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--arb-text-primary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.settings-section-desc {
  font-size: 0.85rem;
  color: var(--arb-text-secondary);
  margin: 0;
}

.bot-status-tag {
  font-size: 0.75rem;
}

.bot-error {
  font-size: 0.82rem;
  color: var(--arb-loss, #ff4757);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}

.bot-control-action {
  display: flex;
  justify-content: flex-start;
}
</style>
