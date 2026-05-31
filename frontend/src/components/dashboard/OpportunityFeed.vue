<script setup lang="ts">
// Imports
import { useOpportunitiesStore } from '@/stores/opportunities.store'
import { useFormatCurrency } from '@/composables/useFormatCurrency'
import { useRelativeTime } from '@/composables/useRelativeTime'
import type { ArbitrageOpportunity, OpportunityStatus } from '@/types'

// Stores y composables
const opportunitiesStore = useOpportunitiesStore()
const { formatUSDT, formatPct } = useFormatCurrency()
const { relativeTime } = useRelativeTime()

// Mapea el status a la severity de PrimeVue Tag
function tagSeverity(status: OpportunityStatus): 'success' | 'danger' | 'info' | 'warn' {
  switch (status) {
    case 'EXECUTED':  return 'success'
    case 'REJECTED':  return 'danger'
    case 'DETECTED':
    case 'EXECUTING': return 'info'
    default:          return 'warn'
  }
}

// Texto compuesto de la operación
function operationText(op: ArbitrageOpportunity): string {
  const buy  = op.buyExchange.charAt(0).toUpperCase()  + op.buyExchange.slice(1)
  const sell = op.sellExchange.charAt(0).toUpperCase() + op.sellExchange.slice(1)
  return `${buy} Ask → ${sell} Bid · ${parseFloat(op.maxVolumeBtc).toFixed(4)} BTC`
}
</script>

<template>
  <div class="feed-panel">
    <h3 class="feed-title">
      FEED DE OPORTUNIDADES
      <span class="feed-count">mostrando últimas 10 de {{ opportunitiesStore.items.length }} en sesión</span>
    </h3>

    <p v-if="opportunitiesStore.items.length === 0" class="feed-empty">
      Esperando oportunidades de arbitraje...
    </p>

    <DataTable
      v-else
      :value="opportunitiesStore.items.slice(0, 10)"
      size="small"
      class="feed-table"
    >
      <!-- Columna estado -->
      <Column header="Estado" style="width: 120px">
        <template #body="{ data }">
          <Tag
            :value="data.status"
            :severity="tagSeverity(data.status)"
          />
        </template>
      </Column>

      <!-- Columna operación -->
      <Column header="Operación">
        <template #body="{ data }">
          <span class="feed-operation">{{ operationText(data) }}</span>
        </template>
      </Column>

      <!-- Columna profit neto -->
      <Column header="Profit neto" style="width: 150px">
        <template #body="{ data }">
          <div class="feed-profit">
            <span
              class="arb-mono"
              :class="parseFloat(data.netProfitUsdt) >= 0 ? 'arb-profit' : 'arb-loss'"
            >
              {{ formatUSDT(data.netProfitUsdt) }}
            </span>
            <small
              :class="parseFloat(data.netProfitPct) >= 0 ? 'arb-profit' : 'arb-loss'"
            >
              ROI {{ formatPct(data.netProfitPct) }}
            </small>
          </div>
        </template>
      </Column>

      <!-- Columna tiempo relativo -->
      <Column header="Hace" style="width: 100px">
        <template #body="{ data }">
          <span class="feed-time">{{ relativeTime(data.detectedAt) }}</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.feed-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
}

.feed-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.feed-count {
  font-weight: 400;
  color: var(--arb-text-muted);
  font-size: 0.7rem;
}

.feed-empty {
  color: var(--arb-text-muted);
  font-size: 0.85rem;
  padding: 1rem 0;
  margin: 0;
}

.feed-operation {
  font-size: 0.8rem;
  color: var(--arb-text-secondary);
}

.feed-profit {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.feed-profit small {
  font-size: 0.7rem;
}

.feed-time {
  font-size: 0.75rem;
  color: var(--arb-text-muted);
}
</style>
