/**
 * Opportunities Store — lista live + historial (límite 500) + paginación lazy (CHG-009).
 * Actualizado via SSE (evento opportunity) y fetchPage para la vista de transacciones.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type {
  ArbitrageOpportunity,
  OpportunityEvent,
  OpportunityFilters,
  PaginatedOpportunitiesResponse,
} from '@/types'
import { useAuthStore } from '@/stores/auth.store'

const MAX_ITEMS = 500

function fromSSEEvent(event: OpportunityEvent): ArbitrageOpportunity {
  return {
    id: event.id,
    buyExchange: event.buy_exchange,
    sellExchange: event.sell_exchange,
    buyPrice: event.buy_price,
    sellPrice: event.sell_price,
    grossSpreadPct: event.gross_spread_pct,
    totalFeesUsdt: event.total_fees_usdt,
    slippageUsdt: event.slippage_usdt,
    netProfitUsdt: event.net_profit_usdt,
    netProfitPct: event.net_profit_pct,
    maxVolumeBtc: event.max_volume_btc,
    strategy: event.strategy,
    score: event.score,
    status: event.status,
    detectedAt: event.detected_at,
    executedAt: null,
    // Desglose de fees (CHG-009)
    tradingFeeBuyUsdt: event.trading_fee_buy_usdt ?? '0',
    tradingFeeSellUsdt: event.trading_fee_sell_usdt ?? '0',
    withdrawalFeeUsdt: event.withdrawal_fee_usdt ?? '0',
    networkLatencyMs: event.network_latency_ms ?? '0',
  }
}

// Mapear respuesta paginada del backend (snake_case → camelCase)
function fromPaginatedItem(raw: Record<string, unknown>): ArbitrageOpportunity {
  return {
    id: raw.id as string,
    buyExchange: raw.buy_exchange as string,
    sellExchange: raw.sell_exchange as string,
    buyPrice: raw.buy_price as string,
    sellPrice: raw.sell_price as string,
    grossSpreadPct: raw.gross_spread_pct as string,
    totalFeesUsdt: raw.total_fees_usdt as string,
    slippageUsdt: raw.slippage_usdt as string,
    netProfitUsdt: raw.net_profit_usdt as string,
    netProfitPct: raw.net_profit_pct as string,
    maxVolumeBtc: raw.max_volume_btc as string,
    strategy: raw.strategy as ArbitrageOpportunity['strategy'],
    score: raw.score as number,
    status: raw.status as ArbitrageOpportunity['status'],
    detectedAt: raw.detected_at as string,
    executedAt: (raw.executed_at as string | null) ?? null,
    // Desglose de fees (CHG-009)
    tradingFeeBuyUsdt: (raw.trading_fee_buy_usdt as string) ?? '0',
    tradingFeeSellUsdt: (raw.trading_fee_sell_usdt as string) ?? '0',
    withdrawalFeeUsdt: (raw.withdrawal_fee_usdt as string) ?? '0',
    networkLatencyMs: (raw.network_latency_ms as string) ?? '0',
  }
}

export const useOpportunitiesStore = defineStore('opportunities', () => {
  // ── Estado live (SSE) ────────────────────────────────────────────────────
  const items = ref<ArbitrageOpportunity[]>([])

  const totalPnlUsdt = computed(() =>
    items.value
      .filter((o) => o.status === 'EXECUTED')
      .reduce((sum, o) => sum + parseFloat(o.netProfitUsdt), 0),
  )

  const executedCount = computed(
    () => items.value.filter((o) => o.status === 'EXECUTED').length,
  )

  function addOpportunity(event: OpportunityEvent): void {
    const opportunity = fromSSEEvent(event)
    items.value.unshift(opportunity)
    // Mantener límite de memoria
    if (items.value.length > MAX_ITEMS) {
      items.value.pop()
    }
  }

  function setItems(list: ArbitrageOpportunity[]): void {
    items.value = list.slice(0, MAX_ITEMS)
  }

  // ── Estado paginado (vista transacciones, CHG-009) ──────────────────────
  const paginatedItems = ref<ArbitrageOpportunity[]>([])
  const totalRecords = ref(0)
  const currentPage = ref(0) // 0-based
  const rowsPerPage = ref(50)
  const loading = ref(false)
  const filters = ref<OpportunityFilters>({})

  async function fetchPage(
    page: number,
    rows: number,
    currentFilters?: OpportunityFilters,
  ): Promise<void> {
    loading.value = true
    try {
      const offset = page * rows
      const params = new URLSearchParams()
      params.set('offset', String(offset))
      params.set('limit', String(rows))
      if (currentFilters?.status?.length) {
        for (const s of currentFilters.status) {
          params.append('status', s)
        }
      }
      if (currentFilters?.buyExchange?.length) {
        for (const e of currentFilters.buyExchange) {
          params.append('buy_exchange', e)
        }
      }
      if (currentFilters?.sellExchange?.length) {
        for (const e of currentFilters.sellExchange) {
          params.append('sell_exchange', e)
        }
      }
      if (currentFilters?.fromDt) params.set('from_dt', currentFilters.fromDt)
      if (currentFilters?.toDt) params.set('to_dt', currentFilters.toDt)

      const authStore = useAuthStore()
      const res = await authStore.fetchWithAuth(`/api/opportunities?${params}`)
      if (res.ok) {
        const data = (await res.json()) as PaginatedOpportunitiesResponse
        // Mapear snake_case → camelCase
        const rawItems = data.items as unknown as Record<string, unknown>[]
        paginatedItems.value = rawItems.map(fromPaginatedItem)
        totalRecords.value = data.total
        currentPage.value = page
        rowsPerPage.value = rows
      }
    } finally {
      loading.value = false
    }
  }

  return {
    // Live SSE
    items,
    totalPnlUsdt,
    executedCount,
    addOpportunity,
    setItems,
    // Paginación lazy (CHG-009)
    paginatedItems,
    totalRecords,
    currentPage,
    rowsPerPage,
    loading,
    filters,
    fetchPage,
  }
})
