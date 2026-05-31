/**
 * Config Store — configuración del bot (capital, threshold, estrategias).
 * Se carga desde GET /api/config al iniciar el dashboard.
 * Se actualiza via PUT /api/config desde SettingsView.
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { BotConfig, ConfigUpdatePayload } from '@/types'
import { useAuthStore } from '@/stores/auth.store'

const DEFAULT_CONFIG: BotConfig = {
  initialCapitalUsdt: '10000.00',
  minProfitThresholdPct: '0.15',
  strategyCrossExchange: true,
  strategyTriangular: false,
  strategyStatistical: false,
  mockModeEnabled: false,
}

export const useConfigStore = defineStore('config', () => {
  const config = ref<BotConfig>({ ...DEFAULT_CONFIG })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchConfig(): Promise<void> {
    const auth = useAuthStore()
    isLoading.value = true
    error.value = null
    try {
      const res = await auth.fetchWithAuth('/api/config')
      if (!res.ok) throw new Error('Error al cargar configuración')
      const data = await res.json() as {
        initial_capital_usdt: string
        min_profit_threshold_pct: string
        strategy_cross_exchange: boolean
        strategy_triangular: boolean
        strategy_statistical: boolean
        mock_mode_enabled: boolean
      }
      config.value = {
        initialCapitalUsdt: data.initial_capital_usdt,
        minProfitThresholdPct: data.min_profit_threshold_pct,
        strategyCrossExchange: data.strategy_cross_exchange,
        strategyTriangular: data.strategy_triangular,
        strategyStatistical: data.strategy_statistical,
        mockModeEnabled: data.mock_mode_enabled,
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
    } finally {
      isLoading.value = false
    }
  }

  async function updateConfig(payload: ConfigUpdatePayload): Promise<void> {
    const auth = useAuthStore()
    isLoading.value = true
    error.value = null
    try {
      const res = await auth.fetchWithAuth('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('Error al actualizar configuración')
      await fetchConfig()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
    } finally {
      isLoading.value = false
    }
  }

  async function toggleMockMode(enabled: boolean): Promise<void> {
    await updateConfig({ mock_mode_enabled: enabled })
  }

  return {
    config,
    isLoading,
    error,
    fetchConfig,
    updateConfig,
    toggleMockMode,
  }
})
