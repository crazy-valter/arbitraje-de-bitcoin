/**
 * usePnLSeries — serie temporal acumulada de P&L para el gráfico.
 *
 * Singleton a nivel de módulo: una sola serie persiste toda la sesión.
 * Se inicializa con las últimas 200 oportunidades EJECUTADAS de la API
 * y se actualiza con cada evento SSE trade_simulated.
 */

import { ref, readonly } from 'vue'
import { useAuthStore } from '@/stores/auth.store'

// [timestamp_ms, pnl_acumulado]
type PnLPoint = [number, number]

// Estado singleton a nivel de módulo
const _series = ref<PnLPoint[]>([])
let _cumulative = 0

export function usePnLSeries() {
  /**
   * Carga las últimas 200 oportunidades ejecutadas para construir la serie inicial.
   * Llamar una sola vez desde PnLChart.vue en onMounted.
   */
  async function loadInitial(): Promise<void> {
    const auth = useAuthStore()
    try {
      const res = await auth.fetchWithAuth('/api/opportunities?limit=200&status=EXECUTED')
      if (!res.ok) return
      const body = await res.json() as { items: Array<{ detected_at: string; executed_at: string | null; net_profit_usdt: string }> }
      const sorted = [...body.items].sort((a, b) => {
        const tsA = new Date(a.executed_at ?? a.detected_at).getTime()
        const tsB = new Date(b.executed_at ?? b.detected_at).getTime()
        return tsA - tsB
      })
      _cumulative = 0
      _series.value = sorted.reduce<PnLPoint[]>((acc, opp) => {
        const profit = parseFloat(opp.net_profit_usdt)
        if (isNaN(profit)) return acc
        _cumulative += profit
        const ts = new Date(opp.executed_at ?? opp.detected_at).getTime()
        acc.push([ts, parseFloat(_cumulative.toFixed(2))])
        return acc
      }, [])
    } catch {
      // Ignorar errores de carga inicial — el gráfico mostrará placeholder vacío
    }
  }

  /**
   * Agrega un punto nuevo a la serie (llamado desde PnLChart al recibir trade_simulated SSE).
   */
  function addPoint(netProfitUsdt: string, timestamp: string): void {
    const profit = parseFloat(netProfitUsdt)
    if (isNaN(profit)) return
    _cumulative += profit
    _series.value = [
      ..._series.value,
      [new Date(timestamp).getTime(), parseFloat(_cumulative.toFixed(2))],
    ]
    // Mantener máximo 500 puntos en memoria
    if (_series.value.length > 500) _series.value = _series.value.slice(-500)
  }

  return { series: readonly(_series), loadInitial, addPoint }
}
