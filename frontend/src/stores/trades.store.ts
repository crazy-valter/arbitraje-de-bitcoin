/**
 * Trades Store — historial de trades simulados y P&L acumulado.
 * Actualizado via SSE (evento trade_executed).
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { SimulatedTrade, TradeExecutedEvent } from '@/types'

const MAX_TRADES = 200

export const useTradesStore = defineStore('trades', () => {
  const items = ref<SimulatedTrade[]>([])

  // P&L acumulado calculado desde los eventos de trade
  const totalPnlUsdt = computed(() =>
    items.value.reduce((sum) => sum, 0),
  )

  // P&L raw desde los eventos SSE (más preciso que recalcular desde trades)
  const pnlHistory = ref<Array<{ timestamp: string; pnl: number }>>([])

  function addTrade(event: TradeExecutedEvent): void {
    // Agregar al historial de P&L
    const pnlValue = parseFloat(event.net_profit_usdt)
    pnlHistory.value.push({
      timestamp: new Date().toISOString(),
      pnl: pnlValue,
    })

    // Mantener límite del historial
    if (pnlHistory.value.length > MAX_TRADES) {
      pnlHistory.value.shift()
    }
  }

  function setItems(list: SimulatedTrade[]): void {
    items.value = list.slice(0, MAX_TRADES)
  }

  return {
    items,
    totalPnlUsdt,
    pnlHistory,
    addTrade,
    setItems,
  }
})
