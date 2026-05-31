<script setup lang="ts">
// Imports
import { computed } from 'vue'
import { useWalletsStore } from '@/stores/wallets.store'
import { useFormatCurrency } from '@/composables/useFormatCurrency'

// Stores y composables
const walletsStore = useWalletsStore()
const { formatUSDTPlain, formatBTC } = useFormatCurrency()

// Renderizado dinámico — deriva filas directamente de los datos del store
// sin WALLET_ORDER hardcodeado. El backend (registry) determina qué exchanges
// y monedas existen. Al agregar un exchange al registry, aparece aquí automáticamente.
const walletRows = computed(() => {
  const list = walletsStore.balanceList
  if (list.length === 0) return []

  return list
    .slice()
    .sort((a, b) => {
      // Ordenar: primero por exchange (alfabético), luego BTC al final
      const exchangeOrder = a.exchange.localeCompare(b.exchange)
      if (exchangeOrder !== 0) return exchangeOrder
      // BTC siempre va después de la moneda fiat del exchange
      if (a.currency === 'BTC') return 1
      if (b.currency === 'BTC') return -1
      return 0
    })
    .map((w) => ({
      label: `${w.exchange.charAt(0).toUpperCase() + w.exchange.slice(1)} ${w.currency}`,
      value: w.balance,
      currency: w.currency,
    }))
})

// Formatea el valor según la moneda
function formatBalance(value: string, currency: string): string {
  if (currency === 'BTC') return formatBTC(value)
  return formatUSDTPlain(value)
}
</script>

<template>
  <div class="wallets-panel">
    <h3 class="wallets-title">WALLETS</h3>

    <!-- Estado de carga -->
    <div v-if="walletsStore.balanceList.length === 0" class="wallets-loading">
      <ProgressSpinner style="width: 24px; height: 24px" />
      <span>Cargando wallets...</span>
    </div>

    <!-- Lista de balances -->
    <div v-else class="wallets-list">
      <div
        v-for="row in walletRows"
        :key="row.label"
        class="wallets-row"
      >
        <span class="wallets-label">{{ row.label }}</span>
        <span class="wallets-value arb-mono">{{ formatBalance(row.value, row.currency) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wallets-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
}

.wallets-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
}

.wallets-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--arb-text-muted);
  font-size: 0.85rem;
  padding: 1rem 0;
}

.wallets-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.wallets-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--arb-border);
  font-size: 0.85rem;
}

.wallets-row:last-child {
  border-bottom: none;
}

.wallets-label {
  color: var(--arb-text-secondary);
}

.wallets-value {
  color: var(--arb-text-primary);
  font-size: 0.85rem;
}
</style>
