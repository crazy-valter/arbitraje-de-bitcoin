/**
 * Wallets Store — balances simulados por exchange y moneda.
 * Actualizado via SSE (evento wallet_update).
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { WalletBalance, WalletUpdateEvent } from '@/types'

export const useWalletsStore = defineStore('wallets', () => {
  // Mapa: `${exchange}:${currency}` → WalletBalance
  const balances = ref<Record<string, WalletBalance>>({})

  const balanceList = computed(() => Object.values(balances.value))

  function updateBalance(event: WalletUpdateEvent): void {
    const key = `${event.exchange}:${event.currency}`
    balances.value[key] = {
      exchange: event.exchange,
      currency: event.currency,
      balance: event.balance,
      updatedAt: event.timestamp,
    }
  }

  function setBalances(list: WalletBalance[]): void {
    balances.value = {}
    list.forEach((b) => {
      const key = `${b.exchange}:${b.currency}`
      balances.value[key] = b
    })
  }

  function getBalance(exchange: string, currency: string): string {
    const key = `${exchange}:${currency}`
    return balances.value[key]?.balance ?? '0'
  }

  return {
    balances,
    balanceList,
    updateBalance,
    setBalances,
    getBalance,
  }
})
