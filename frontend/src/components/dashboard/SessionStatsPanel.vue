<script setup lang="ts">
// Imports
import { computed } from 'vue'
import { useMetricsStore } from '@/stores/metrics.store'
import { useOpportunitiesStore } from '@/stores/opportunities.store'
import { useFormatCurrency } from '@/composables/useFormatCurrency'

// Stores y composables
const metricsStore       = useMetricsStore()
const opportunitiesStore = useOpportunitiesStore()
const { formatUSDT }     = useFormatCurrency()

// Uptime reactivo — llega via SSE metrics_update cada 5 segundos
const uptimeHours = computed(() => metricsStore.metrics.uptimeSeconds / 3600)

// Oportunidades por hora — denominador se actualiza junto con el uptime
const opportunitiesPerHour = computed(() => {
  const total = metricsStore.metrics.opportunitiesTotal
  return (total / Math.max(uptimeHours.value, 0.001)).toFixed(1)
})

// Ganancia promedio por operación ejecutada
const avgProfitPerTrade = computed(() => {
  const executed = metricsStore.metrics.executedTotal
  const total    = metricsStore.metrics.totalPnlUsdt
  if (executed === 0) return '$0.00'
  return formatUSDT(total / executed)
})

// Oportunidades descartadas (status REJECTED)
const rejectedCount = computed(() =>
  opportunitiesStore.items.filter((o) => o.status === 'REJECTED').length
)

// Formatear uptime como "Xh Ym"
const uptimeFormatted = computed(() => {
  const s = metricsStore.metrics.uptimeSeconds
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}h ${m}m`
})

// Filas de la tabla de estadísticas
const statsRows = computed(() => [
  { label: 'Oportunidades/hora', value: opportunitiesPerHour.value },
  { label: 'Tasa de ejecución',  value: `${metricsStore.metrics.winRatePct.toFixed(1)}%` },
  { label: 'Ganancia promedio',  value: avgProfitPerTrade.value },
  { label: 'Descartadas',        value: String(rejectedCount.value) },
  { label: 'Tiempo activo',      value: uptimeFormatted.value },
])
</script>

<template>
  <div class="stats-panel">
    <h3 class="stats-title">ESTADÍSTICAS DE SESIÓN</h3>

    <div class="stats-list">
      <div
        v-for="row in statsRows"
        :key="row.label"
        class="stats-row"
      >
        <span class="stats-label">{{ row.label }}</span>
        <span class="stats-value arb-mono">{{ row.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
}

.stats-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
}

.stats-list {
  display: flex;
  flex-direction: column;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--arb-border);
  font-size: 0.85rem;
}

.stats-row:last-child {
  border-bottom: none;
}

.stats-label {
  color: var(--arb-text-secondary);
}

.stats-value {
  color: var(--arb-text-primary);
  font-size: 0.85rem;
}
</style>
