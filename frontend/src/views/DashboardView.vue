<script setup lang="ts">
// Imports
import { computed, onMounted } from 'vue'
import { useSSE } from '@/composables/useSSE'
import { useFormatCurrency } from '@/composables/useFormatCurrency'
import { useRelativeTime } from '@/composables/useRelativeTime'
import { useAuthStore } from '@/stores/auth.store'
import { useMetricsStore } from '@/stores/metrics.store'
import { useWalletsStore } from '@/stores/wallets.store'
import { useOpportunitiesStore } from '@/stores/opportunities.store'

// Componentes del dashboard
import MetricCard          from '@/components/common/MetricCard.vue'
import PnLChart            from '@/components/charts/PnLChart.vue'
import OrderBookPanel      from '@/components/orderbook/OrderBookPanel.vue'
import OpportunityFeed     from '@/components/dashboard/OpportunityFeed.vue'
import WalletsPanel        from '@/components/dashboard/WalletsPanel.vue'
import BotStatusPanel      from '@/components/dashboard/BotStatusPanel.vue'
import SessionStatsPanel   from '@/components/dashboard/SessionStatsPanel.vue'

// Stores y composables
const { connect }            = useSSE()
const { formatUSDT, formatUSDTPlain } = useFormatCurrency()
const { relativeTime }       = useRelativeTime()
const metricsStore           = useMetricsStore()
const walletsStore           = useWalletsStore()
const opportunitiesStore     = useOpportunitiesStore()
const authStore              = useAuthStore()

// Conectar SSE y cargar balances iniciales al montar el dashboard
onMounted(async () => {
  connect()
  // Seed inicial de wallets desde la API — evita spinner permanente en WalletsPanel
  try {
    const res = await authStore.fetchWithAuth('/api/wallets')
    if (res.ok) {
      const data = await res.json() as {
        items: Array<{ exchange: string; currency: string; balance: string; updated_at: string | null }>
      }
      walletsStore.setBalances(
        data.items.map((item) => ({
          exchange: item.exchange,
          currency: item.currency,
          balance: item.balance,
          updatedAt: item.updated_at,
        })),
      )
    }
  } catch {
    // Error no crítico — los balances llegarán por SSE
  }
})

// ── KPI Cards ────────────────────────────────────────────────────────────────

// Card 1: P&L acumulado
const pnlValue = computed(() => formatUSDT(metricsStore.metrics.totalPnlUsdt))
const pnlTrend = computed(() =>
  metricsStore.metrics.totalPnlUsdt >= 0 ? 'up' : 'down'
)

// Card 2: Oportunidades detectadas
const opportunitiesValue = computed(() =>
  metricsStore.metrics.opportunitiesTotal.toString()
)
const opportunitiesSubvalue = computed(() => {
  const last = opportunitiesStore.items[0]
  if (!last) return ''
  return `última ${relativeTime(last.detectedAt)}`
})

// Card 3: Operaciones ejecutadas — contador de sesión (se reinicia con el backend)
const executedValue = computed(() =>
  metricsStore.metrics.executedTotal.toString()
)
const executedSubvalue = computed(() =>
  `sesión actual · tasa ${metricsStore.metrics.winRatePct.toFixed(1)}%`
)

// Card 4: Capital en operación (suma de balances USDT de todos los wallets)
const capitalValue = computed(() => {
  const total = walletsStore.balanceList
    .filter((w) => w.currency === 'USDT' || w.currency === 'USD')
    .reduce((sum, w) => sum + parseFloat(w.balance), 0)
  return formatUSDTPlain(total)
})
const capitalSubvalue = computed(() => {
  const activeWallets = walletsStore.balanceList.filter(
    (w) => parseFloat(w.balance) > 0
  ).length
  return `${activeWallets} wallets activas`
})
</script>

<template>
  <div class="dashboard">

    <!-- Sección 1: 4 KPI Cards -->
    <section class="dashboard-section dashboard-kpis">
      <MetricCard
        label="P&L Acumulado"
        :value="pnlValue"
        :trend="pnlTrend"
      />
      <MetricCard
        label="Oportunidades Detectadas"
        :value="opportunitiesValue"
        :subvalue="opportunitiesSubvalue"
        trend="neutral"
      />
      <MetricCard
        label="Operaciones Ejecutadas"
        :value="executedValue"
        :subvalue="executedSubvalue"
        trend="neutral"
      />
      <MetricCard
        label="Capital en Operación"
        :value="capitalValue"
        :subvalue="capitalSubvalue"
        trend="neutral"
      />
    </section>

    <!-- Sección 2: Gráfico P&L + Order Book (proporción 7/5) -->
    <section class="dashboard-section dashboard-charts">
      <div class="dashboard-chart-left">
        <PnLChart />
      </div>
      <div class="dashboard-chart-right">
        <OrderBookPanel />
      </div>
    </section>

    <!-- Sección 3: Feed de oportunidades (full width) -->
    <section class="dashboard-section">
      <OpportunityFeed />
    </section>

    <!-- Sección 4: 3 paneles informativos -->
    <section class="dashboard-section dashboard-panels">
      <WalletsPanel />
      <BotStatusPanel />
      <SessionStatsPanel />
    </section>

  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Sección 1: 4 columnas de KPIs */
.dashboard-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

/* Sección 2: gráfico (flex-grow 7) + order book (flex-grow 5) */
.dashboard-charts {
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: 1rem;
}

.dashboard-chart-left,
.dashboard-chart-right {
  min-width: 0; /* evita overflow en grid */
}

/* Sección 4: 3 paneles iguales */
.dashboard-panels {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

/* ── Responsividad ─── */
@media (max-width: 960px) {
  .dashboard-kpis {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-charts {
    grid-template-columns: 1fr;
  }

  .dashboard-panels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .dashboard-kpis {
    grid-template-columns: 1fr;
  }
}
</style>
