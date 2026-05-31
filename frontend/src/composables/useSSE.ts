/**
 * useSSE — composable singleton para la conexión SSE autenticada.
 *
 * Singleton a nivel de módulo: una sola conexión persiste toda la sesión,
 * independientemente de qué vista esté activa.
 *
 * Características:
 * - withCredentials: true (envía cookies HttpOnly automáticamente)
 * - Backoff exponencial: 2s → 4s → 8s → ... → 30s máx
 * - Cada tipo de evento se enruta al store correspondiente
 */

import { computed, ref } from 'vue'
import { useMarketStore } from '@/stores/market.store'
import { useOpportunitiesStore } from '@/stores/opportunities.store'
import { useTradesStore } from '@/stores/trades.store'
import { useWalletsStore } from '@/stores/wallets.store'
import { useMetricsStore } from '@/stores/metrics.store'
import type {
  OrderBookUpdate,
  OpportunityEvent,
  TradeExecutedEvent,
  WalletUpdateEvent,
  MetricsUpdateEvent,
} from '@/types'

// Estado a nivel de módulo — persiste entre montajes y desmontajes de componentes
let _eventSource: EventSource | null = null
let _retryTimeout: ReturnType<typeof setTimeout> | null = null
let _retryDelay = 2_000  // backoff exponencial

// ref reactivo — Vue detecta cambios y re-renderiza el indicador de estado
const _isConnected = ref(false)

const EVENT_HANDLERS: Record<string, (data: unknown) => void> = {
  orderbook_update: (d) => useMarketStore().updateOrderBook(d as OrderBookUpdate),
  opportunity_detected: (d) => useOpportunitiesStore().addOpportunity(d as OpportunityEvent),
  trade_simulated: (d) => useTradesStore().addTrade(d as TradeExecutedEvent),
  wallet_update: (d) => useWalletsStore().updateBalance(d as WalletUpdateEvent),
  metrics_update: (d) => useMetricsStore().update(d as MetricsUpdateEvent),
}

function openEventSource(): void {
  // withCredentials: true — el browser envía las cookies HttpOnly automáticamente
  _eventSource = new EventSource('/events', { withCredentials: true })

  // Registrar un listener por tipo de evento
  for (const [eventType, handler] of Object.entries(EVENT_HANDLERS)) {
    _eventSource.addEventListener(eventType, (e: MessageEvent) => {
      try {
        handler(JSON.parse(e.data as string))
      } catch {
        // Ignorar eventos malformados
      }
    })
  }

  _eventSource.onopen = () => {
    _retryDelay = 2_000  // resetear backoff al reconectar con éxito
    _isConnected.value = true
  }

  _eventSource.onerror = () => {
    _eventSource?.close()
    _eventSource = null
    _isConnected.value = false
    // Backoff exponencial hasta 30s
    _retryTimeout = setTimeout(() => {
      _retryDelay = Math.min(_retryDelay * 2, 30_000)
      openEventSource()
    }, _retryDelay)
  }
}

export function useSSE() {
  const isConnected = computed(() => _isConnected.value)

  function connect(): void {
    if (_eventSource !== null) return  // ya conectado
    openEventSource()
  }

  function disconnect(): void {
    if (_retryTimeout !== null) {
      clearTimeout(_retryTimeout)
      _retryTimeout = null
    }
    _eventSource?.close()
    _eventSource = null
    _isConnected.value = false
  }

  return { isConnected, connect, disconnect }
}
