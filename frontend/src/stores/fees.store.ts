/**
 * Fees Store — comisiones configurables por exchange (buy/sell).
 * Los valores se almacenan como multiplicadores (ej. 0.001 = 0.1%).
 * El backend recibe/envía porcentajes (ej. "0.10" = 0.10%).
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ExchangeFeeInfo, ExchangeFeeUpdatePayload } from '@/types'
import { useAuthStore } from './auth.store'

export const useFeesStore = defineStore('fees', () => {
  const fees    = ref<ExchangeFeeInfo[]>([])
  const loading = ref(false)
  const error   = ref<string | null>(null)

  /**
   * Retorna el multiplicador de comisión para el exchange y lado dados.
   * Si el exchange no está en el store retorna 0.001 como fallback seguro.
   */
  function getFee(exchangeId: string, side: 'buy' | 'sell'): number {
    const entry = fees.value.find(
      (f) => f.exchange_id === exchangeId.toLowerCase(),
    )
    if (!entry) return 0.001
    return side === 'buy'
      ? parseFloat(entry.fee_buy)
      : parseFloat(entry.fee_sell)
  }

  /**
   * Carga las comisiones desde GET /api/fees.
   * Requiere sesión activa — usa fetchWithAuth.
   */
  async function fetchFees(): Promise<void> {
    const authStore = useAuthStore()
    loading.value = true
    error.value   = null
    try {
      const res = await authStore.fetchWithAuth('/api/fees')
      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { detail?: string }
        error.value = body.detail ?? `Error ${res.status} al cargar comisiones`
        return
      }
      const data = await res.json() as { fees: ExchangeFeeInfo[] }
      fees.value = data.fees
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
    } finally {
      loading.value = false
    }
  }

  /**
   * Actualiza las comisiones de un exchange via PUT /api/fees/{exchangeId}.
   * El payload contiene porcentajes como strings (ej. "0.10").
   */
  async function updateFee(
    exchangeId: string,
    payload: ExchangeFeeUpdatePayload,
  ): Promise<void> {
    const authStore = useAuthStore()
    error.value = null
    try {
      const res = await authStore.fetchWithAuth(
        `/api/fees/${exchangeId.toLowerCase()}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )
      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(body.detail ?? `Error ${res.status} al actualizar comisión`)
      }
      // Actualizar el store local con los nuevos valores devueltos por el backend
      const updated = await res.json() as ExchangeFeeInfo
      const idx = fees.value.findIndex(
        (f) => f.exchange_id === exchangeId.toLowerCase(),
      )
      if (idx !== -1) {
        fees.value[idx] = updated
      } else {
        fees.value.push(updated)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      throw err  // re-lanzar para que el componente pueda mostrar feedback
    }
  }

  return { fees, loading, error, getFee, fetchFees, updateFee }
})
