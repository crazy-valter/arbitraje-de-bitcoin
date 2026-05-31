<script setup lang="ts">
// 1. Imports
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import { useFormatCurrency } from '@/composables/useFormatCurrency'
import { useAuthStore } from '@/stores/auth.store'
import type { ArbitrageOpportunity, OpportunityStatus, SimulatedTrade } from '@/types'

// 2. Props y emits
const props = defineProps<{
  opportunity: ArbitrageOpportunity | null
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// 3. Composables
const { formatUSDT, formatUSDTPlain, formatBTC, formatPct } = useFormatCurrency()
const authStore = useAuthStore()

// 4. State local para trades
const trades = ref<SimulatedTrade[]>([])
const tradesLoading = ref(false)

// 5. Computed
const showDialog = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val),
})

const isExecuted = computed(
  () => props.opportunity?.status === 'EXECUTED',
)

// Severidad del Tag según status
function tagSeverity(status: OpportunityStatus): 'success' | 'danger' | 'info' | 'warn' {
  switch (status) {
    case 'EXECUTED':  return 'success'
    case 'REJECTED':  return 'danger'
    case 'FAILED':    return 'warn'
    case 'DETECTED':
    case 'EXECUTING': return 'info'
    default:          return 'warn'
  }
}

// Formatear fecha ISO a formato local legible
function formatDateTime(isoString: string | null): string {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return d.toLocaleString('es-MX', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

// Texto legible de la estrategia
function strategyLabel(strategy: string): string {
  const map: Record<string, string> = {
    cross_exchange: 'Cross-Exchange',
    triangular: 'Triangular',
    statistical: 'Estadistico',
  }
  return map[strategy] ?? strategy
}

// Decisión según status
function decisionText(op: ArbitrageOpportunity): string {
  if (op.status === 'EXECUTED') return 'Ejecutada (profit neto positivo)'
  if (op.status === 'REJECTED') return 'Rechazada (profit neto negativo o bajo threshold)'
  if (op.status === 'FAILED') return 'Fallida (error en ejecucion)'
  if (op.status === 'EXECUTING') return 'En ejecucion...'
  return 'Detectada (pendiente de evaluacion)'
}

// Color de clase CSS para profit
function profitClass(value: string): string {
  const n = parseFloat(value)
  return n >= 0 ? 'arb-profit' : 'arb-loss'
}

// Datos de wallets para la tabla (construidos desde trades reales)
interface WalletRow {
  exchange: string
  usdtBefore: string
  usdtAfter: string
  btcBefore: string
  btcAfter: string
}

const walletRows = computed<WalletRow[]>(() => {
  if (!props.opportunity || !isExecuted.value || trades.value.length === 0) return []
  const op = props.opportunity
  // Buscar el trade de compra y el de venta
  const buyTrade = trades.value.find((t) => t.exchange === op.buyExchange)
  const sellTrade = trades.value.find((t) => t.exchange === op.sellExchange)
  const rows: WalletRow[] = []
  if (buyTrade) {
    rows.push({
      exchange: buyTrade.exchange,
      usdtBefore: formatUSDTPlain(buyTrade.walletUsdtBefore),
      usdtAfter: formatUSDTPlain(buyTrade.walletUsdtAfter),
      btcBefore: formatBTC(buyTrade.walletBtcBefore),
      btcAfter: formatBTC(buyTrade.walletBtcAfter),
    })
  }
  if (sellTrade && sellTrade.exchange !== (buyTrade?.exchange ?? '')) {
    rows.push({
      exchange: sellTrade.exchange,
      usdtBefore: formatUSDTPlain(sellTrade.walletUsdtBefore),
      usdtAfter: formatUSDTPlain(sellTrade.walletUsdtAfter),
      btcBefore: formatBTC(sellTrade.walletBtcBefore),
      btcAfter: formatBTC(sellTrade.walletBtcAfter),
    })
  }
  return rows
})

// 6. Fetch trades cuando se abre el dialog para una oportunidad EXECUTED
async function fetchTrades(opportunityId: string): Promise<void> {
  tradesLoading.value = true
  trades.value = []
  try {
    const res = await authStore.fetchWithAuth(`/api/trades?opportunity_id=${opportunityId}`)
    if (res.ok) {
      const data = (await res.json()) as { items: Record<string, unknown>[]; total: number }
      trades.value = data.items.map((raw) => ({
        id: raw.id as string,
        opportunityId: raw.opportunity_id as string,
        side: raw.side as string,
        exchange: raw.exchange as string,
        price: raw.price as string,
        volumeBtc: raw.volume_btc as string,
        feeUsdt: raw.fee_usdt as string,
        slippageUsdt: raw.slippage_usdt as string,
        executedAt: raw.executed_at as string,
        isPartial: raw.is_partial as boolean,
        status: raw.status as string,
        walletUsdtBefore: raw.wallet_usdt_before as string,
        walletUsdtAfter: raw.wallet_usdt_after as string,
        walletBtcBefore: raw.wallet_btc_before as string,
        walletBtcAfter: raw.wallet_btc_after as string,
      }))
    }
  } finally {
    tradesLoading.value = false
  }
}

// Disparar fetch cuando el dialog se abre con una oportunidad EXECUTED
watch(
  () => [props.visible, props.opportunity?.id, props.opportunity?.status],
  ([visible, id, status]) => {
    if (visible && id && status === 'EXECUTED') {
      fetchTrades(id as string)
    } else if (!visible) {
      trades.value = []
    }
  },
)
</script>

<template>
  <Dialog
    v-model:visible="showDialog"
    :modal="true"
    :maximizable="true"
    :closable="true"
    :draggable="false"
    class="opportunity-detail-dialog"
    :header="opportunity ? `Detalle de Operacion #${opportunity.id.slice(0, 8).toUpperCase()}` : 'Detalle'"
  >
    <template v-if="opportunity">
      <!-- Cabecera: estado, fechas, estrategia -->
      <div class="detail-header">
        <div class="detail-header-row">
          <div class="detail-field">
            <span class="detail-label">Estado</span>
            <Tag
              :value="opportunity.status"
              :severity="tagSeverity(opportunity.status)"
            />
          </div>
          <div class="detail-field">
            <span class="detail-label">Estrategia</span>
            <span class="detail-value">{{ strategyLabel(opportunity.strategy) }}</span>
          </div>
          <div class="detail-field">
            <span class="detail-label">Score</span>
            <span class="detail-value arb-mono">{{ opportunity.score.toFixed(3) }}</span>
          </div>
        </div>
        <div class="detail-header-row">
          <div class="detail-field">
            <span class="detail-label">Detectada</span>
            <span class="detail-value arb-mono">{{ formatDateTime(opportunity.detectedAt) }}</span>
          </div>
          <div class="detail-field" v-if="opportunity.executedAt">
            <span class="detail-label">Ejecutada</span>
            <span class="detail-value arb-mono">{{ formatDateTime(opportunity.executedAt) }}</span>
          </div>
        </div>
      </div>

      <!-- Seccion Compra / Venta -->
      <div class="detail-section">
        <h4 class="detail-section-title">COMPRA / VENTA</h4>
        <div class="detail-grid-2col">
          <!-- Compra -->
          <div class="detail-card">
            <div class="detail-card-title">COMPRA</div>
            <div class="detail-card-row">
              <span class="detail-label">Exchange</span>
              <span class="detail-value exchange-name" :class="`exchange-${opportunity.buyExchange}`">
                {{ opportunity.buyExchange.charAt(0).toUpperCase() + opportunity.buyExchange.slice(1) }}
              </span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Precio Ask</span>
              <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.buyPrice) }}</span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Fee trading</span>
              <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.tradingFeeBuyUsdt) }}</span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Fee retiro</span>
              <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.withdrawalFeeUsdt) }}</span>
            </div>
          </div>
          <!-- Venta -->
          <div class="detail-card">
            <div class="detail-card-title">VENTA</div>
            <div class="detail-card-row">
              <span class="detail-label">Exchange</span>
              <span class="detail-value exchange-name" :class="`exchange-${opportunity.sellExchange}`">
                {{ opportunity.sellExchange.charAt(0).toUpperCase() + opportunity.sellExchange.slice(1) }}
              </span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Precio Bid</span>
              <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.sellPrice) }}</span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Fee trading</span>
              <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.tradingFeeSellUsdt) }}</span>
            </div>
            <div class="detail-card-row">
              <span class="detail-label">Volumen BTC</span>
              <span class="detail-value arb-mono">{{ formatBTC(opportunity.maxVolumeBtc) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Analisis de Costos -->
      <div class="detail-section">
        <h4 class="detail-section-title">ANALISIS DE COSTOS</h4>
        <div class="detail-card">
          <div class="detail-card-row">
            <span class="detail-label">Spread bruto</span>
            <span class="detail-value arb-mono">
              {{ formatUSDTPlain(
                (parseFloat(opportunity.sellPrice) - parseFloat(opportunity.buyPrice))
                * parseFloat(opportunity.maxVolumeBtc)
              ) }}
              <small class="detail-pct">({{ formatPct(opportunity.grossSpreadPct) }})</small>
            </span>
          </div>
          <div class="detail-card-row">
            <span class="detail-label">Fee trading compra</span>
            <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.tradingFeeBuyUsdt) }}</span>
          </div>
          <div class="detail-card-row">
            <span class="detail-label">Fee trading venta</span>
            <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.tradingFeeSellUsdt) }}</span>
          </div>
          <div class="detail-card-row">
            <span class="detail-label">Slippage estimado</span>
            <span class="detail-value arb-mono">{{ formatUSDTPlain(opportunity.slippageUsdt) }}</span>
          </div>
          <div class="detail-card-row">
            <span class="detail-label">Latencia estimada (ms)</span>
            <span class="detail-value arb-mono">{{ opportunity.networkLatencyMs }}</span>
          </div>
          <div class="detail-card-divider"></div>
          <div class="detail-card-row">
            <span class="detail-label"><strong>Total costos</strong></span>
            <span class="detail-value arb-mono"><strong>{{ formatUSDTPlain(opportunity.totalFeesUsdt) }}</strong></span>
          </div>
          <div class="detail-card-row">
            <span class="detail-label"><strong>Profit NETO</strong></span>
            <span class="detail-value arb-mono" :class="profitClass(opportunity.netProfitUsdt)">
              <strong>{{ formatUSDT(opportunity.netProfitUsdt) }}</strong>
              <small class="detail-pct">({{ formatPct(opportunity.netProfitPct) }})</small>
            </span>
          </div>
          <div class="detail-card-row detail-decision">
            <span class="detail-label">Decision:</span>
            <span class="detail-value" :class="profitClass(opportunity.netProfitUsdt)">
              {{ decisionText(opportunity) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Estado de Wallets (solo si EXECUTED) -->
      <div class="detail-section" v-if="isExecuted">
        <h4 class="detail-section-title">ESTADO DE WALLETS</h4>
        <!-- Loading de trades -->
        <div v-if="tradesLoading" class="wallets-loading">
          <ProgressSpinner style="width: 24px; height: 24px" stroke-width="3" />
          <span class="wallets-loading-text">Cargando snapshots...</span>
        </div>
        <!-- Tabla con datos reales -->
        <DataTable
          v-else-if="walletRows.length > 0"
          :value="walletRows"
          size="small"
          class="detail-wallets-table"
        >
          <Column field="exchange" header="Exchange">
            <template #body="{ data }">
              <span class="exchange-name" :class="`exchange-${data.exchange}`">
                {{ data.exchange.charAt(0).toUpperCase() + data.exchange.slice(1) }}
              </span>
            </template>
          </Column>
          <Column field="usdtBefore" header="USDT antes">
            <template #body="{ data }">
              <span class="arb-mono">{{ data.usdtBefore }}</span>
            </template>
          </Column>
          <Column field="usdtAfter" header="USDT despues">
            <template #body="{ data }">
              <span class="arb-mono">{{ data.usdtAfter }}</span>
            </template>
          </Column>
          <Column field="btcBefore" header="BTC antes">
            <template #body="{ data }">
              <span class="arb-mono">{{ data.btcBefore }}</span>
            </template>
          </Column>
          <Column field="btcAfter" header="BTC despues">
            <template #body="{ data }">
              <span class="arb-mono">{{ data.btcAfter }}</span>
            </template>
          </Column>
        </DataTable>
        <p v-else class="detail-wallets-note">
          No se encontraron snapshots de wallet para esta operacion.
        </p>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
/* Dialog ancho */
.opportunity-detail-dialog :deep(.p-dialog) {
  width: 60vw !important;
  max-width: 95vw;
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
}

.opportunity-detail-dialog :deep(.p-dialog-header) {
  background: var(--arb-bg-elevated);
  border-bottom: 1px solid var(--arb-border);
  color: var(--arb-text-primary);
  padding: 0.75rem 1rem;
}

.opportunity-detail-dialog :deep(.p-dialog-content) {
  background: var(--arb-bg-surface);
  color: var(--arb-text-primary);
  padding: 1rem;
}

.opportunity-detail-dialog :deep(.p-dialog-title) {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--arb-text-primary);
}

/* Cabecera */
.detail-header {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--arb-border);
}

.detail-header-row {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.5rem;
}

.detail-header-row:last-child {
  margin-bottom: 0;
}

/* Secciones */
.detail-section {
  margin-bottom: 1rem;
}

.detail-section-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 0.5rem;
  text-transform: uppercase;
}

/* Grid 2 columnas para compra/venta */
.detail-grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

/* Card individual */
.detail-card {
  background: var(--arb-bg-elevated);
  border: 1px solid var(--arb-border);
  border-radius: 6px;
  padding: 0.75rem;
}

.detail-card-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

/* Filas dentro de cards */
.detail-card-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.2rem 0;
}

.detail-card-divider {
  border-top: 1px solid var(--arb-border);
  margin: 0.5rem 0;
}

.detail-decision {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--arb-border);
}

/* Labels y valores */
.detail-label {
  font-size: 0.78rem;
  color: var(--arb-text-secondary);
}

.detail-value {
  font-size: 0.82rem;
  color: var(--arb-text-primary);
}

.detail-pct {
  margin-left: 0.25rem;
  font-size: 0.7rem;
}

.detail-field {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

/* Colores de exchange */
.exchange-name {
  font-weight: 600;
  font-size: 0.85rem;
}

.exchange-binance {
  color: var(--arb-binance);
}

.exchange-kraken {
  color: var(--arb-kraken);
}

.exchange-bybit {
  color: var(--arb-bybit);
}

/* Tabla wallets */
.detail-wallets-table {
  font-size: 0.8rem;
}

/* Loading wallets */
.wallets-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0;
}

.wallets-loading-text {
  font-size: 0.8rem;
  color: var(--arb-text-muted);
}

.detail-wallets-note {
  font-size: 0.7rem;
  color: var(--arb-text-muted);
  font-style: italic;
  margin: 0.5rem 0 0;
}

/* Responsive */
@media (max-width: 768px) {
  .opportunity-detail-dialog :deep(.p-dialog) {
    width: 95vw !important;
  }

  .detail-grid-2col {
    grid-template-columns: 1fr;
  }

  .detail-header-row {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
