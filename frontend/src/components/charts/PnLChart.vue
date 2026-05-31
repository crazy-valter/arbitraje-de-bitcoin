<script setup lang="ts">
// Imports
import { computed, onMounted, watch } from 'vue'
import Chart from 'primevue/chart'
import { useTradesStore } from '@/stores/trades.store'
import { usePnLSeries } from '@/composables/usePnLSeries'

// Stores y composables
const tradesStore = useTradesStore()
const { series, loadInitial, addPoint } = usePnLSeries()

// Datos reactivos del gráfico — se reconstruyen cada vez que cambia la serie
const chartData = computed(() => ({
  labels: series.value.map(([ts]) =>
    new Date(ts).toLocaleTimeString('es', { timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit' })
  ),
  datasets: [
    {
      label: 'P&L acumulado',
      data: series.value.map(([, pnl]) => pnl),
      fill: true,
      borderColor: '#00d4aa',
      backgroundColor: 'rgba(0, 212, 170, 0.1)',
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2,
    },
  ],
}))

// Opciones estáticas del gráfico con tema oscuro
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 300 },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: { parsed: { y: number } }) =>
          `$${Number(ctx.parsed.y).toFixed(2)}`,
      },
    },
  },
  scales: {
    x: {
      grid: { color: '#30363d' },
      ticks: { color: '#a0aec0', maxTicksLimit: 6 },
    },
    y: {
      grid: { color: '#30363d' },
      ticks: {
        color: '#a0aec0',
        callback: (v: number | string) => `$${v}`,
      },
    },
  },
}

// Carga inicial en onMounted — solo una vez (singleton)
onMounted(async () => {
  await loadInitial()
})

// Watch al pnlHistory del trades store para agregar puntos nuevos via SSE
watch(
  () => tradesStore.pnlHistory.length,
  (newLen, oldLen) => {
    if (newLen > oldLen) {
      const last = tradesStore.pnlHistory[newLen - 1]
      if (last) {
        addPoint(String(last.pnl), last.timestamp)
      }
    }
  }
)
</script>

<template>
  <div class="pnl-panel">
    <h3 class="pnl-title">P&L EN EL TIEMPO</h3>
    <div v-if="series.length === 0" class="pnl-empty">
      <i class="pi pi-chart-line pnl-empty-icon" />
      <p>Sin operaciones ejecutadas aún</p>
    </div>
    <div v-else class="pnl-chart-wrapper">
      <Chart
        type="line"
        :data="chartData"
        :options="chartOptions"
        style="height: 300px"
      />
    </div>
  </div>
</template>

<style scoped>
.pnl-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
}

.pnl-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
}

.pnl-chart-wrapper {
  height: 300px;
}

.pnl-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--arb-text-muted);
  gap: 0.5rem;
}

.pnl-empty-icon {
  font-size: 2rem;
  opacity: 0.4;
}

.pnl-empty p {
  margin: 0;
  font-size: 0.85rem;
}
</style>
