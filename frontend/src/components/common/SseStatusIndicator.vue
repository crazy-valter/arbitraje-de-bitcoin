<script setup lang="ts">
import { computed } from 'vue'
import { useSSE } from '@/composables/useSSE'
import { useConfigStore } from '@/stores/config.store'

const { isConnected } = useSSE()
const configStore     = useConfigStore()

const isMockMode = computed(() => configStore.config.mockModeEnabled)

// Tres estados: desconectado | demo | en vivo
const dotClass = computed(() => {
  if (!isConnected.value) return 'sse-dot--off'
  return isMockMode.value ? 'sse-dot--demo' : 'sse-dot--on'
})

const label = computed(() => {
  if (!isConnected.value) return 'Desconectado'
  return isMockMode.value ? 'Demo' : 'En vivo'
})

const title = computed(() => {
  if (!isConnected.value) return 'SSE desconectado — reconectando...'
  return isMockMode.value
    ? 'Modo Demo activo — datos sintéticos'
    : 'SSE conectado — datos en tiempo real'
})
</script>

<template>
  <div class="sse-indicator" :title="title">
    <span class="sse-dot" :class="dotClass" />
    <span class="sse-label" :class="{ 'sse-label--demo': isConnected && isMockMode }">
      {{ label }}
    </span>
  </div>
</template>

<style scoped>
.sse-indicator {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  cursor: default;
}

.sse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sse-dot--on {
  background: var(--arb-profit);
  box-shadow: 0 0 6px var(--arb-profit);
  animation: sse-pulse 2s infinite;
}

.sse-dot--demo {
  background: var(--arb-warning);
  box-shadow: 0 0 6px var(--arb-warning);
  animation: sse-pulse 2s infinite;
}

.sse-dot--off {
  background: var(--arb-loss);
}

.sse-label {
  color: var(--arb-text-secondary);
}

.sse-label--demo {
  color: var(--arb-warning);
}

@keyframes sse-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}
</style>
