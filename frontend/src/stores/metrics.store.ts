/**
 * Metrics Store — métricas agregadas del sistema.
 * Actualizado via SSE (evento metrics_update, cada 5 segundos).
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { SystemMetrics, MetricsUpdateEvent } from '@/types'

const DEFAULT_METRICS: SystemMetrics = {
  opportunitiesTotal: 0,
  executedTotal: 0,
  winRatePct: 0,
  totalPnlUsdt: 0,
  connectedExchanges: 0,
  exchangeLatencies: {},
  uptimeSeconds: 0,
  timestamp: new Date().toISOString(),
}

export const useMetricsStore = defineStore('metrics', () => {
  const metrics = ref<SystemMetrics>({ ...DEFAULT_METRICS })

  // BUGFIX: los campos correctos son opportunities_detected y trades_simulated,
  // no opportunities_total / executed_total (que no existen en el evento SSE)
  function update(event: MetricsUpdateEvent): void {
    metrics.value = {
      opportunitiesTotal: event.opportunities_detected,
      executedTotal: event.trades_simulated,
      winRatePct: event.win_rate_pct,
      totalPnlUsdt: event.total_pnl_usdt,
      connectedExchanges: event.connected_exchanges,
      exchangeLatencies: event.exchange_latencies ?? {},
      uptimeSeconds: event.uptime_seconds ?? 0,
      timestamp: event.timestamp,
    }
  }

  function setFromApi(data: SystemMetrics): void {
    metrics.value = { ...data }
  }

  return {
    metrics,
    update,
    setFromApi,
  }
})
