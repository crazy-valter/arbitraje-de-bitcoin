/**
 * Exchanges Store — listado de exchanges del registry con su estado is_active.
 * Se carga desde GET /api/exchanges al iniciar el dashboard o la vista Settings.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ExchangeInfo } from '@/types'
import { useAuthStore } from '@/stores/auth.store'

export const useExchangesStore = defineStore('exchanges', () => {
  // Lista de exchanges del registry
  const exchanges = ref<ExchangeInfo[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Exchanges activos
  const activeExchanges = computed(() =>
    exchanges.value.filter((ex) => ex.is_active),
  )

  // Exchanges core (no desactivables desde UI)
  const coreExchanges = computed(() =>
    exchanges.value.filter((ex) => ex.core),
  )

  /**
   * Carga la lista de exchanges desde el backend.
   */
  async function fetchExchanges(): Promise<void> {
    const auth = useAuthStore()
    isLoading.value = true
    error.value = null
    try {
      const res = await auth.fetchWithAuth('/api/exchanges')
      if (!res.ok) throw new Error(`Error al cargar exchanges: ${res.status}`)
      const data = await res.json() as { items: ExchangeInfo[] }
      exchanges.value = data.items
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Activa o desactiva un exchange no-core.
   * Retorna el exchange actualizado o lanza error si el backend responde con error.
   */
  async function toggleExchange(exchangeId: string): Promise<ExchangeInfo | null> {
    const auth = useAuthStore()
    error.value = null
    try {
      const res = await auth.fetchWithAuth(`/api/exchanges/${exchangeId}/toggle`, {
        method: 'PUT',
      })
      if (res.status === 403) {
        error.value = 'Este exchange es core y no puede ser desactivado.'
        return null
      }
      if (!res.ok) throw new Error(`Error al toggle exchange: ${res.status}`)
      const updated = await res.json() as ExchangeInfo

      // Actualizar el estado local en el store
      const idx = exchanges.value.findIndex((ex) => ex.exchange_id === exchangeId)
      if (idx !== -1) {
        exchanges.value[idx] = updated
      }
      return updated
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      return null
    }
  }

  return {
    exchanges,
    isLoading,
    error,
    activeExchanges,
    coreExchanges,
    fetchExchanges,
    toggleExchange,
  }
})
