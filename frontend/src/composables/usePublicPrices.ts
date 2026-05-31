/**
 * usePublicPrices — polling de precios BTC/USDT públicos cada 3 segundos.
 *
 * Endpoint público sin autenticación: GET /api/public/prices
 * Usa fetch sin credentials (endpoint público).
 */

import { ref, onMounted, onUnmounted } from 'vue'

export interface ExchangePrice {
  exchange: string // "binance" | "bybit" | "kraken"
  symbol: string // "BTC/USDT"
  ask: string // Decimal string
  bid: string // Decimal string
  mid: string // Decimal string
  is_stale: boolean
  updated_at: string // ISO 8601
}

export function usePublicPrices() {
  const prices = ref<ExchangePrice[]>([])
  const isLoading = ref(false)
  const lastError = ref<string | null>(null)
  let intervalId: ReturnType<typeof setInterval> | null = null

  async function fetchPrices(): Promise<void> {
    try {
      const response = await fetch('/api/public/prices', {
        credentials: 'omit', // endpoint público, sin cookies
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      prices.value = data.prices ?? []
      lastError.value = null
    } catch (err) {
      lastError.value = err instanceof Error ? err.message : 'Error de conexión'
      // Mantener los últimos valores válidos en prices
    } finally {
      if (isLoading.value) {
        isLoading.value = false
      }
    }
  }

  onMounted(async () => {
    isLoading.value = true
    await fetchPrices() // primer fetch inmediato
    intervalId = setInterval(fetchPrices, 3000) // polling cada 3s
  })

  onUnmounted(() => {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
  })

  return { prices, isLoading, lastError }
}
