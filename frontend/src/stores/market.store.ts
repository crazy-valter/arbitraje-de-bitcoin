/**
 * Market Store — order books en tiempo real por exchange.
 * Actualizado via SSE (evento orderbook_update).
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ExchangeOrderBook, OrderBookUpdate } from '@/types'

export const useMarketStore = defineStore('market', () => {
  // Mapa de exchange → datos del order book
  const orderBooks = ref<Record<string, ExchangeOrderBook>>({})

  const exchangeList = computed(() => Object.values(orderBooks.value))

  function updateOrderBook(data: OrderBookUpdate): void {
    orderBooks.value[data.exchange] = {
      exchange: data.exchange,
      ask: data.ask,
      bid: data.bid,
      timestamp: data.timestamp,
      isStale: false,
    }
  }

  function getOrderBook(exchange: string): ExchangeOrderBook | null {
    return orderBooks.value[exchange] ?? null
  }

  return {
    orderBooks,
    exchangeList,
    updateOrderBook,
    getOrderBook,
  }
})
