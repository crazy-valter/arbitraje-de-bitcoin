<script setup lang="ts">
// Imports
import { computed, onMounted } from 'vue'
import { useMetricsStore } from '@/stores/metrics.store'
import { useConfigStore } from '@/stores/config.store'

// Stores
const metricsStore = useMetricsStore()
const configStore  = useConfigStore()

// Carga config si no está disponible todavía
onMounted(async () => {
  if (!configStore.config || configStore.config.initialCapitalUsdt === '10000.00') {
    await configStore.fetchConfig()
  }
})

const isMockMode = computed(() => configStore.config.mockModeEnabled)

// Conectividad WS: OK si todos los exchanges tienen latencia >= 0
const allFeedsConnected = computed(() => {
  const latencies = metricsStore.metrics.exchangeLatencies
  const values = Object.values(latencies)
  if (values.length === 0) return false
  return values.every((v) => v >= 0)
})

// Lista de exchanges con su estado de latencia
const exchangeStatuses = computed(() => {
  const latencies = metricsStore.metrics.exchangeLatencies
  return Object.entries(latencies).map(([exchange, ms]) => ({
    name: exchange.charAt(0).toUpperCase() + exchange.slice(1),
    ms,
    connected: ms >= 0,
  }))
})
</script>

<template>
  <div class="bot-panel">
    <h3 class="bot-title">ESTADO DEL BOT</h3>

    <!-- Sección de exchanges WebSocket -->
    <div class="bot-section">
      <div class="bot-section-label">
        Exchanges
        <span v-if="isMockMode" class="bot-mock-badge">DEMO</span>
      </div>
      <div
        v-if="exchangeStatuses.length === 0"
        class="bot-no-data"
      >
        Esperando métricas...
      </div>
      <div
        v-for="ex in exchangeStatuses"
        :key="ex.name"
        class="bot-exchange-row"
      >
        <span
          class="bot-dot"
          :class="ex.connected ? 'bot-dot--on' : 'bot-dot--off'"
        />
        <span class="bot-exchange-name">{{ ex.name }}</span>
        <span class="bot-latency" :class="{ 'bot-latency--mock': isMockMode && ex.connected }">
          {{ ex.connected ? (isMockMode ? `${ex.ms}ms (mock)` : `${ex.ms}ms`) : 'Desconectado' }}
        </span>
      </div>
    </div>

    <!-- Sección de parámetros -->
    <div class="bot-section">
      <div class="bot-section-label">Parámetros</div>
      <div class="bot-param-row">
        <span class="bot-param-label">Umbral mínimo ROI</span>
        <span class="arb-mono bot-param-value">{{ configStore.config.minProfitThresholdPct }}%</span>
      </div>
      <div class="bot-param-row">
        <span class="bot-param-label">Capital máx/op</span>
        <span class="arb-mono bot-param-value">${{ configStore.config.initialCapitalUsdt }}</span>
      </div>
      <div class="bot-param-row">
        <span class="bot-param-label">Conectividad WS</span>
        <span
          class="bot-circuit"
          :class="allFeedsConnected ? 'bot-circuit--ok' : 'bot-circuit--alert'"
        >
          {{ allFeedsConnected ? 'OK' : 'ALERTA' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bot-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
}

.bot-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
}

.bot-section {
  margin-bottom: 1rem;
}

.bot-section-label {
  font-size: 0.7rem;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--arb-border);
}

.bot-no-data {
  font-size: 0.8rem;
  color: var(--arb-text-muted);
  font-style: italic;
  padding: 0.25rem 0;
}

.bot-exchange-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  font-size: 0.85rem;
}

.bot-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bot-dot--on  { background: var(--arb-profit); box-shadow: 0 0 4px var(--arb-profit); }
.bot-dot--off { background: var(--arb-loss); }

.bot-mock-badge {
  font-size: 0.6rem;
  font-weight: 700;
  background: rgba(255, 165, 2, 0.2);
  color: var(--arb-warning);
  border: 1px solid var(--arb-warning);
  border-radius: 3px;
  padding: 0.05rem 0.3rem;
  margin-left: 0.4rem;
  vertical-align: middle;
}

.bot-latency--mock {
  color: var(--arb-warning);
}

.bot-exchange-name {
  flex: 1;
  color: var(--arb-text-primary);
  font-weight: 500;
}

.bot-latency {
  color: var(--arb-text-secondary);
  font-size: 0.75rem;
}

.bot-param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.35rem 0;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--arb-border);
}

.bot-param-row:last-child {
  border-bottom: none;
}

.bot-param-label {
  color: var(--arb-text-secondary);
}

.bot-param-value {
  color: var(--arb-text-primary);
  font-size: 0.8rem;
}

.bot-circuit {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
}

.bot-circuit--ok    { color: var(--arb-profit); background: rgba(0, 212, 170, 0.15); }
.bot-circuit--alert { color: var(--arb-warning); background: rgba(255, 165, 2, 0.15); }
</style>
