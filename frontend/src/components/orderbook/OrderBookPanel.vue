<script setup lang="ts">
// Imports
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market.store'
import { useFeesStore } from '@/stores/fees.store'
import { useFormatCurrency } from '@/composables/useFormatCurrency'

import { useConfigStore } from '@/stores/config.store'

// Stores y composables
const marketStore  = useMarketStore()
const feesStore    = useFeesStore()
const configStore  = useConfigStore()
const { formatUSDT } = useFormatCurrency()

function exchangeLabel(id: string): string {
  const base = id.charAt(0).toUpperCase() + id.slice(1)
  return configStore.config.mockModeEnabled ? `${base}-demo` : base
}

// Mapa de exchanges a sus variables CSS de color de marca
const EXCHANGE_COLOR: Record<string, string> = {
  binance: 'var(--arb-binance)',
  bybit:   'var(--arb-bybit)',
  kraken:  'var(--arb-kraken)',
}

/**
 * Calcula la divergencia máxima entre todos los pares (A, B) de exchanges.
 * Para cada par: spread_bruto = bid[B] - ask[A]
 * Si es positivo, existe oportunidad de arbitraje antes de fees.
 */
const bestDivergence = computed(() => {
  const list = marketStore.exchangeList
  if (list.length < 2) return null

  let maxSpread = -Infinity
  let bestBuyExchange = ''
  let bestSellExchange = ''

  for (const obA of list) {
    for (const obB of list) {
      if (obA.exchange === obB.exchange) continue
      const ask = parseFloat(obA.ask)
      const bid = parseFloat(obB.bid)
      if (isNaN(ask) || isNaN(bid)) continue
      const spread = bid - ask
      if (spread > maxSpread) {
        maxSpread = spread
        bestBuyExchange = obA.exchange
        bestSellExchange = obB.exchange
      }
    }
  }

  if (maxSpread <= 0 || !bestBuyExchange) return null

  // Calcular spread neto post-fees
  const buyOb = marketStore.getOrderBook(bestBuyExchange)
  const sellOb = marketStore.getOrderBook(bestSellExchange)
  if (!buyOb || !sellOb) return null

  const ask = parseFloat(buyOb.ask)
  const bid = parseFloat(sellOb.bid)
  const feeBuy  = feesStore.getFee(bestBuyExchange, 'buy')
  const feeSell = feesStore.getFee(bestSellExchange, 'sell')

  // Spread neto = bid*(1-feeSell) - ask*(1+feeBuy)
  const netSpread = bid * (1 - feeSell) - ask * (1 + feeBuy)
  const netPct    = (netSpread / ask) * 100

  return {
    grossSpread: maxSpread,
    netSpread,
    netPct,
    buyExchange: bestBuyExchange,
    sellExchange: bestSellExchange,
  }
})
</script>

<template>
  <div class="ob-panel">
    <h3 class="ob-title">ORDER BOOK EN VIVO</h3>

    <!-- Tabla de Ask / Bid por exchange -->
    <div v-if="marketStore.exchangeList.length === 0" class="ob-empty">
      Esperando datos de exchanges...
    </div>
    <table v-else class="ob-table">
      <thead>
        <tr>
          <th class="ob-th">Exchange</th>
          <th class="ob-th ob-th--right">Ask (USDT)</th>
          <th class="ob-th ob-th--right">Bid (USDT)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="ob in marketStore.exchangeList" :key="ob.exchange" class="ob-row">
          <td class="ob-td">
            <span
              class="ob-exchange-name"
              :style="{ color: EXCHANGE_COLOR[ob.exchange.toLowerCase()] ?? 'var(--arb-text-primary)' }"
            >
              {{ exchangeLabel(ob.exchange) }}
            </span>
          </td>
          <td class="ob-td ob-td--right">
            <span class="arb-mono arb-loss">{{ formatUSDT(ob.ask) }}</span>
          </td>
          <td class="ob-td ob-td--right">
            <span class="arb-mono arb-profit">{{ formatUSDT(ob.bid) }}</span>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Sección de divergencia actual -->
    <div class="ob-divergence">
      <div class="ob-divergence-title">Divergencia actual</div>

      <div v-if="bestDivergence" class="ob-divergence-content">
        <div class="ob-divergence-main">
          <span class="arb-mono arb-profit ob-divergence-amount">
            {{ formatUSDT(bestDivergence.grossSpread) }}
          </span>
          <span class="ob-divergence-direction">
            {{ exchangeLabel(bestDivergence.buyExchange) }}
            →
            {{ exchangeLabel(bestDivergence.sellExchange) }}
          </span>
        </div>
        <div
          class="ob-divergence-net"
          :class="bestDivergence.netSpread > 0 ? 'arb-profit' : 'arb-loss'"
        >
          neto post-fees:
          {{ formatUSDT(bestDivergence.netSpread) }}
          · ROI {{ bestDivergence.netPct.toFixed(3) }}%
        </div>
      </div>

      <div v-else class="ob-divergence-none">
        Sin divergencia rentable
      </div>
    </div>
  </div>
</template>

<style scoped>
.ob-panel {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
}

.ob-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
  text-transform: uppercase;
}

.ob-empty {
  color: var(--arb-text-muted);
  font-size: 0.85rem;
  padding: 1rem 0;
}

.ob-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

.ob-th {
  font-size: 0.7rem;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid var(--arb-border);
  text-align: left;
}

.ob-th--right { text-align: right; }

.ob-row:hover {
  background: var(--arb-bg-elevated);
}

.ob-td {
  padding: 0.5rem 0.5rem;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--arb-border);
}

.ob-td--right { text-align: right; }

.ob-exchange-name {
  font-weight: 600;
  font-size: 0.85rem;
}

/* Sección divergencia */
.ob-divergence {
  border-top: 1px solid var(--arb-border);
  padding-top: 0.75rem;
  margin-top: 0.25rem;
}

.ob-divergence-title {
  font-size: 0.7rem;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.ob-divergence-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.ob-divergence-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.ob-divergence-amount {
  font-size: 1.1rem;
  font-weight: 700;
}

.ob-divergence-direction {
  font-size: 0.8rem;
  color: var(--arb-text-secondary);
}

.ob-divergence-net {
  font-size: 0.75rem;
}

.ob-divergence-none {
  font-size: 0.85rem;
  color: var(--arb-text-muted);
  font-style: italic;
}
</style>
