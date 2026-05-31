<script setup lang="ts">
// 1. Imports
import { ref, onMounted, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import ProgressSpinner from 'primevue/progressspinner'
import { useOpportunitiesStore } from '@/stores/opportunities.store'
import { useFormatCurrency } from '@/composables/useFormatCurrency'
import type { ArbitrageOpportunity, OpportunityStatus } from '@/types'
import OpportunityDetailDialog from '@/components/transactions/OpportunityDetailDialog.vue'

// Cabeceras CSV para la exportacion
const CSV_HEADERS = [
  'ID', 'Fecha/Hora', 'Comprar en', 'Precio compra', 'Vender en', 'Precio venta',
  'Spread bruto %', 'Fees totales USDT', 'Profit neto USDT', 'Profit neto %', 'Estado', 'Estrategia',
]

// 2. Stores y composables
const opportunitiesStore = useOpportunitiesStore()
const { formatUSDT, formatUSDTPlain, formatPct } = useFormatCurrency()

// 3. State local
const detailVisible = ref(false)
const selectedOpportunity = ref<ArbitrageOpportunity | null>(null)

// Opciones para filtros
const statusOptions: { label: string; value: OpportunityStatus }[] = [
  { label: 'Detectada', value: 'DETECTED' },
  { label: 'Ejecutando', value: 'EXECUTING' },
  { label: 'Ejecutada', value: 'EXECUTED' },
  { label: 'Rechazada', value: 'REJECTED' },
  { label: 'Fallida', value: 'FAILED' },
]

const exchangeOptions: { label: string; value: string }[] = [
  { label: 'Binance', value: 'binance' },
  { label: 'Bybit', value: 'bybit' },
  { label: 'Kraken', value: 'kraken' },
]

// Filtros reactivos
const filterStatus = ref<OpportunityStatus[]>([])
const filterBuyExchange = ref<string[]>([])
const filterSellExchange = ref<string[]>([])

// Paginacion
const firstRow = ref(0)
const pageRows = ref(50)

// 4. Computed
const totalRecords = computed(() => opportunitiesStore.totalRecords)
const loading = computed(() => opportunitiesStore.loading)
const paginatedItems = computed(() => opportunitiesStore.paginatedItems)

// 5. Funciones / handlers

// Severidad del Tag segun status
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

// Clase CSS para profit (positivo/negativo)
function profitClass(value: string): string {
  const n = parseFloat(value)
  return n >= 0 ? 'arb-profit' : 'arb-loss'
}

// Formatear fecha para la tabla — siempre en zona horaria America/Mexico_City
function formatDate(isoString: string): string {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return d.toLocaleString('es-MX', {
    timeZone: 'America/Mexico_City',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

// Formatear fecha ISO completa para tooltip
function formatISODate(isoString: string): string {
  if (!isoString) return ''
  return isoString
}

// Tooltip con desglose de fees
function feesTooltip(op: ArbitrageOpportunity): string {
  const buy = parseFloat(op.tradingFeeBuyUsdt)
  const sell = parseFloat(op.tradingFeeSellUsdt)
  const withdrawal = parseFloat(op.withdrawalFeeUsdt)
  const slippage = parseFloat(op.slippageUsdt)
  const latency = parseFloat(op.networkLatencyMs)
  return [
    `Trading compra: ${formatUSDTPlain(buy)}`,
    `Trading venta: ${formatUSDTPlain(sell)}`,
    `Retiro: ${formatUSDTPlain(withdrawal)}`,
    `Slippage: ${formatUSDTPlain(slippage)}`,
    `Latencia: ${formatUSDTPlain(latency)}`,
  ].join('\n')
}

// Indice visual descendente (el mas reciente tiene el numero mas alto)
function rowIndex(slotIndex: number): number {
  return totalRecords.value - firstRow.value - slotIndex
}

// Abrir dialog de detalle
function openDetail(op: ArbitrageOpportunity): void {
  selectedOpportunity.value = op
  detailVisible.value = true
}

// Handler de paginacion lazy
function onPage(event: { first: number; rows: number; page: number }): void {
  firstRow.value = event.first
  pageRows.value = event.rows
  loadPage(event.page, event.rows)
}

// Construir filtros y llamar fetchPage
function loadPage(page: number, rows: number): void {
  const currentFilters = {
    status: filterStatus.value.length > 0 ? filterStatus.value : undefined,
    buyExchange: filterBuyExchange.value.length > 0 ? filterBuyExchange.value : undefined,
    sellExchange: filterSellExchange.value.length > 0 ? filterSellExchange.value : undefined,
  }
  opportunitiesStore.fetchPage(page, rows, currentFilters)
}

// Aplicar filtros — reiniciar a pagina 0
function applyFilters(): void {
  firstRow.value = 0
  loadPage(0, pageRows.value)
}

// Exportar dataset actual como CSV
function exportCSV(): void {
  const items = paginatedItems.value
  if (items.length === 0) return

  const rows = items.map((op) => [
    op.id,
    op.detectedAt,
    op.buyExchange,
    op.buyPrice,
    op.sellExchange,
    op.sellPrice,
    op.grossSpreadPct,
    op.totalFeesUsdt,
    op.netProfitUsdt,
    op.netProfitPct,
    op.status,
    op.strategy,
  ])

  const csvContent = [
    CSV_HEADERS.join(','),
    ...rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `transacciones_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

// 6. Lifecycle
onMounted(() => {
  loadPage(0, pageRows.value)
})
</script>

<template>
  <div class="transactions-view">
    <!-- Cabecera -->
    <div class="transactions-header">
      <div class="transactions-title-row">
        <h1 class="transactions-title">Transacciones Simuladas</h1>
        <Tag value="Historial completo" severity="secondary" class="scope-tag" />
        <Button
          label="Exportar CSV"
          icon="pi pi-download"
          severity="secondary"
          outlined
          size="small"
          :disabled="paginatedItems.length === 0"
          @click="exportCSV"
        />
      </div>
      <div class="transactions-filters">
        <div class="filter-group">
          <label class="filter-label">Estado</label>
          <MultiSelect
            v-model="filterStatus"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            placeholder="Todos"
            class="filter-multiselect"
            :max-selected-labels="2"
            @change="applyFilters"
          />
        </div>
        <div class="filter-group">
          <label class="filter-label">Comprar en</label>
          <MultiSelect
            v-model="filterBuyExchange"
            :options="exchangeOptions"
            option-label="label"
            option-value="value"
            placeholder="Todos"
            class="filter-multiselect"
            :max-selected-labels="2"
            @change="applyFilters"
          />
        </div>
        <div class="filter-group">
          <label class="filter-label">Vender en</label>
          <MultiSelect
            v-model="filterSellExchange"
            :options="exchangeOptions"
            option-label="label"
            option-value="value"
            placeholder="Todos"
            class="filter-multiselect"
            :max-selected-labels="2"
            @change="applyFilters"
          />
        </div>
      </div>
      <!-- Nota informativa sobre el ciclo de vida de las oportunidades -->
      <div class="lifecycle-note">
        <i class="pi pi-info-circle" />
        Las oportunidades con estado <strong>DETECTED</strong> aparecen en el Feed del Dashboard en tiempo real,
        pero se resuelven a <strong>EXECUTED</strong> o <strong>REJECTED</strong> antes de persistirse.
        El historial completo está disponible con los filtros de estado.
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading && paginatedItems.length === 0" class="transactions-loading">
      <ProgressSpinner
        style="width: 40px; height: 40px"
        stroke-width="3"
      />
      <span class="loading-text">Cargando transacciones...</span>
    </div>

    <!-- DataTable -->
    <DataTable
      v-else
      :value="paginatedItems"
      :lazy="true"
      :paginator="true"
      :rows="pageRows"
      :rowsPerPageOptions="[25, 50, 100]"
      :total-records="totalRecords"
      :first="firstRow"
      :loading="loading"
      @page="onPage"
      size="small"
      class="transactions-table"
      empty-message="Sin transacciones registradas"
      striped-rows
    >
      <!-- Columna indice -->
      <Column header="#" style="width: 50px">
        <template #body="{ index }">
          <span class="arb-mono row-index">{{ rowIndex(index) }}</span>
        </template>
      </Column>

      <!-- Columna Fecha/Hora -->
      <Column header="Fecha/Hora" style="width: 140px">
        <template #body="{ data }">
          <span
            class="arb-mono"
            v-tooltip="formatISODate(data.detectedAt)"
          >
            {{ formatDate(data.detectedAt) }}
          </span>
        </template>
      </Column>

      <!-- Columna Comprar en -->
      <Column header="Comprar en" style="width: 160px">
        <template #body="{ data }">
          <div class="exchange-cell">
            <span class="exchange-name" :class="`exchange-${data.buyExchange}`">
              {{ data.buyExchange.charAt(0).toUpperCase() + data.buyExchange.slice(1) }}
            </span>
            <span class="arb-mono exchange-price">{{ formatUSDTPlain(data.buyPrice) }}</span>
          </div>
        </template>
      </Column>

      <!-- Columna Vender en -->
      <Column header="Vender en" style="width: 160px">
        <template #body="{ data }">
          <div class="exchange-cell">
            <span class="exchange-name" :class="`exchange-${data.sellExchange}`">
              {{ data.sellExchange.charAt(0).toUpperCase() + data.sellExchange.slice(1) }}
            </span>
            <span class="arb-mono exchange-price">{{ formatUSDTPlain(data.sellPrice) }}</span>
          </div>
        </template>
      </Column>

      <!-- Columna Spread Bruto -->
      <Column header="Spread Bruto" style="width: 110px">
        <template #body="{ data }">
          <span
            class="arb-mono"
            :class="parseFloat(data.grossSpreadPct) < 0.3 ? 'spread-low' : ''"
          >
            {{ formatPct(data.grossSpreadPct) }}
          </span>
        </template>
      </Column>

      <!-- Columna Fees Totales -->
      <Column header="Fees" style="width: 110px" class="col-fees">
        <template #body="{ data }">
          <span
            class="arb-mono"
            v-tooltip="feesTooltip(data)"
          >
            {{ formatUSDTPlain(data.totalFeesUsdt) }}
          </span>
        </template>
      </Column>

      <!-- Columna Profit Neto -->
      <Column header="Profit Neto" style="width: 160px">
        <template #body="{ data }">
          <div class="profit-cell">
            <span
              class="arb-mono"
              :class="profitClass(data.netProfitUsdt)"
            >
              {{ formatUSDT(data.netProfitUsdt) }}
            </span>
            <small
              class="arb-mono"
              :class="profitClass(data.netProfitPct)"
            >
              {{ formatPct(data.netProfitPct) }}
            </small>
          </div>
        </template>
      </Column>

      <!-- Columna Decision (status) -->
      <Column header="Decision" style="width: 120px">
        <template #body="{ data }">
          <Tag
            :value="data.status"
            :severity="tagSeverity(data.status)"
          />
        </template>
      </Column>

      <!-- Columna Acciones -->
      <Column header="" style="width: 50px">
        <template #body="{ data }">
          <Button
            icon="pi pi-eye"
            severity="secondary"
            text
            rounded
            size="small"
            @click="openDetail(data)"
            v-tooltip="'Ver detalle'"
          />
        </template>
      </Column>
    </DataTable>

    <!-- Dialog de detalle -->
    <OpportunityDetailDialog
      v-model:visible="detailVisible"
      :opportunity="selectedOpportunity"
    />
  </div>
</template>

<style scoped>
.transactions-view {
  padding: 1rem;
}

/* Cabecera */
.transactions-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.transactions-title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.transactions-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--arb-text-primary);
  margin: 0;
}

.transactions-filters {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.filter-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.filter-multiselect {
  min-width: 140px;
  max-width: 200px;
}

.scope-tag {
  font-size: 0.7rem;
}

.lifecycle-note {
  width: 100%;
  font-size: 0.78rem;
  color: var(--arb-text-muted);
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  line-height: 1.5;
}

.lifecycle-note .pi-info-circle {
  color: var(--arb-accent);
  margin-top: 0.15rem;
  flex-shrink: 0;
}

.lifecycle-note strong {
  color: var(--arb-text-secondary);
}

/* Loading */
.transactions-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem;
  justify-content: center;
}

.loading-text {
  color: var(--arb-text-secondary);
  font-size: 0.85rem;
}

/* Tabla */
.transactions-table {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  overflow: hidden;
}

/* Indice de fila */
.row-index {
  color: var(--arb-text-muted);
  font-size: 0.75rem;
}

/* Celda de exchange */
.exchange-cell {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.exchange-name {
  font-weight: 600;
  font-size: 0.8rem;
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

.exchange-price {
  font-size: 0.75rem;
  color: var(--arb-text-secondary);
}

/* Spread bajo — color warning */
.spread-low {
  color: var(--arb-warning);
}

/* Celda de profit */
.profit-cell {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.profit-cell small {
  font-size: 0.7rem;
}

/* Responsive: ocultar columnas secundarias en mobile */
@media (max-width: 768px) {
  .transactions-header {
    flex-direction: column;
  }

  .transactions-filters {
    width: 100%;
  }

  .col-fees {
    display: none;
  }

  :deep(.transactions-table) .col-fees {
    display: none;
  }
}
</style>
