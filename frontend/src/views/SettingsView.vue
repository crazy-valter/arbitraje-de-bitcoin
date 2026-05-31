<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useExchangesStore } from '@/stores/exchanges.store'
import { useWalletsStore } from '@/stores/wallets.store'
import { useFeesStore } from '@/stores/fees.store'
import { useAuthStore } from '@/stores/auth.store'
import { useConfigStore } from '@/stores/config.store'
import type { WalletSetBalancePayload, WalletSetBalanceResponse } from '@/types'
import MockModeCard    from '@/components/settings/MockModeCard.vue'
import BotControlCard from '@/components/settings/BotControlCard.vue'

const exchangesStore = useExchangesStore()
const walletsStore   = useWalletsStore()
const feesStore      = useFeesStore()
const authStore      = useAuthStore()
const configStore    = useConfigStore()

const globalError = ref<string | null>(null)

// ── Config capital / threshold ────────────────────────────────────────────────
const configCapital    = ref<number>(0)
const configThreshold  = ref<number>(0)
// Config modal
const configModalVisible   = ref(false)
const configModalCapital   = ref<number>(0)
const configModalThreshold = ref<number>(0)
const configModalSaving    = ref(false)
const configModalError     = ref<string | null>(null)
const configModalSuccess   = ref(false)

// Sincronizar display con el store cuando cambie config
watch(
  () => configStore.config,
  (cfg) => {
    configCapital.value   = parseFloat(cfg.initialCapitalUsdt)
    configThreshold.value = parseFloat(cfg.minProfitThresholdPct)
  },
  { immediate: true },
)

function openConfigModal(): void {
  configModalCapital.value   = configCapital.value
  configModalThreshold.value = configThreshold.value
  configModalError.value     = null
  configModalSuccess.value   = false
  configModalVisible.value   = true
}

function closeConfigModal(): void {
  configModalVisible.value = false
}

async function saveConfigModal(): Promise<void> {
  configModalSaving.value  = true
  configModalError.value   = null
  configModalSuccess.value = false
  await configStore.updateConfig({
    initial_capital_usdt:     configModalCapital.value.toFixed(2),
    min_profit_threshold_pct: configModalThreshold.value.toFixed(2),
  })
  if (configStore.error) {
    configModalError.value  = configStore.error
    configModalSaving.value = false
  } else {
    configModalSuccess.value = true
    setTimeout(() => {
      configModalVisible.value = false
      configModalSuccess.value = false
    }, 1200)
    configModalSaving.value = false
  }
}

// ── Wallet modal ──────────────────────────────────────────────────────────────
const walletModalVisible  = ref(false)
const walletModalExchange = ref<string>('')
const walletModalInputs   = ref<Record<string, string>>({
  USDT: '0.00',
  BTC:  '0.00000000',
  ETH:  '0.0000000',
})
const walletModalSnapshot = ref<Record<string, string>>({})
const walletModalSaving   = ref(false)
const walletModalError    = ref<string | null>(null)
const walletModalSuccess  = ref(false)

// ── Fee modal ─────────────────────────────────────────────────────────────────
const feeModalVisible  = ref(false)
const feeModalExchange = ref<string>('')
const feeModalBuy      = ref<number>(0.10)   // en porcentaje: 0.10 = 0.10%
const feeModalSell     = ref<number>(0.10)
const feeModalSaving   = ref(false)
const feeModalError    = ref<string | null>(null)
const feeModalSuccess  = ref(false)

// ── Constantes ────────────────────────────────────────────────────────────────
const CORE_EXCHANGES = ['binance', 'bybit', 'kraken']
const CURRENCIES     = ['USDT', 'BTC', 'ETH'] as const

// ── Helpers ───────────────────────────────────────────────────────────────────
function getDisplayName(exchangeId: string): string {
  const found = exchangesStore.exchanges.find((e) => e.exchange_id === exchangeId)
  return found?.display_name ?? (exchangeId.charAt(0).toUpperCase() + exchangeId.slice(1))
}

// ── Computed: filas wallets ───────────────────────────────────────────────────
interface WalletRow {
  exchangeId:  string
  displayName: string
  usdt: string
  btc:  string
  eth:  string
}

const walletRows = computed<WalletRow[]>(() =>
  CORE_EXCHANGES.map((exId) => {
    const usdtN = parseFloat(walletsStore.getBalance(exId, 'USDT'))
    const btcN  = parseFloat(walletsStore.getBalance(exId, 'BTC'))
    const ethN  = parseFloat(walletsStore.getBalance(exId, 'ETH'))
    return {
      exchangeId:  exId,
      displayName: getDisplayName(exId),
      usdt: isNaN(usdtN) ? '0.00'       : usdtN.toFixed(2),
      btc:  isNaN(btcN)  ? '0.00000000' : btcN.toFixed(8),
      eth:  isNaN(ethN)  ? '0.0000000'  : ethN.toFixed(7),
    }
  }),
)

// ── Computed: filas fees ──────────────────────────────────────────────────────
interface FeeRow {
  exchangeId:    string
  displayName:   string
  feeBuyDisplay: string
  feeSellDisplay: string
}

const feeRows = computed<FeeRow[]>(() =>
  CORE_EXCHANGES.map((exId) => ({
    exchangeId:    exId,
    displayName:   getDisplayName(exId),
    feeBuyDisplay:  (feesStore.getFee(exId, 'buy')  * 100).toFixed(2) + '%',
    feeSellDisplay: (feesStore.getFee(exId, 'sell') * 100).toFixed(2) + '%',
  })),
)

// ── Computed: títulos de modales ──────────────────────────────────────────────
const walletModalTitle = computed(() => `Editar wallets — ${getDisplayName(walletModalExchange.value)}`)
const feeModalTitle    = computed(() => `Editar comisiones — ${getDisplayName(feeModalExchange.value)}`)

// ── onMounted ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await configStore.fetchConfig()
  await exchangesStore.fetchExchanges()

  if (walletsStore.balanceList.length === 0) {
    try {
      const res = await authStore.fetchWithAuth('/api/wallets')
      if (res.ok) {
        const data = await res.json() as {
          items: Array<{ exchange: string; currency: string; balance: string; updated_at: string | null }>
        }
        walletsStore.setBalances(
          data.items.map((item) => ({
            exchange:  item.exchange,
            currency:  item.currency,
            balance:   item.balance,
            updatedAt: item.updated_at,
          })),
        )
      }
    } catch { /* silent — valores se mostrarán en 0 */ }
  }

  await feesStore.fetchFees()
})

// ── Wallet modal: funciones ───────────────────────────────────────────────────
function openWalletModal(row: WalletRow): void {
  walletModalExchange.value = row.exchangeId
  walletModalInputs.value   = { USDT: row.usdt, BTC: row.btc, ETH: row.eth }
  walletModalSnapshot.value = { ...walletModalInputs.value }
  walletModalError.value    = null
  walletModalSuccess.value  = false
  walletModalVisible.value  = true
}

function closeWalletModal(): void {
  walletModalVisible.value = false
}

const INCREMENTS: Record<string, number> = {
  USDT: 100,
  BTC:  0.00000001,
  ETH:  0.0000001,
}

function adjustBalance(currency: string, direction: 1 | -1): void {
  const step    = INCREMENTS[currency] ?? 1
  const current = parseFloat(walletModalInputs.value[currency]) || 0
  const clamped = Math.max(0, current + direction * step)
  if (currency === 'USDT')     walletModalInputs.value[currency] = clamped.toFixed(2)
  else if (currency === 'BTC') walletModalInputs.value[currency] = clamped.toFixed(8)
  else                          walletModalInputs.value[currency] = clamped.toFixed(7)
}

function formatOnBlur(currency: string): void {
  const n = parseFloat(walletModalInputs.value[currency])
  const safe = isNaN(n) || n < 0 ? 0 : n
  if (currency === 'USDT')     walletModalInputs.value[currency] = safe.toFixed(2)
  else if (currency === 'BTC') walletModalInputs.value[currency] = safe.toFixed(8)
  else                          walletModalInputs.value[currency] = safe.toFixed(7)
}

async function saveWalletModal(): Promise<void> {
  walletModalSaving.value  = true
  walletModalError.value   = null
  walletModalSuccess.value = false

  const exchange = walletModalExchange.value
  const changed  = CURRENCIES.filter(
    (c) => walletModalInputs.value[c] !== walletModalSnapshot.value[c],
  )

  if (changed.length === 0) {
    walletModalVisible.value = false
    walletModalSaving.value  = false
    return
  }

  try {
    for (const currency of changed) {
      const rawValue = walletModalInputs.value[currency]
      const parsed   = parseFloat(rawValue)
      if (isNaN(parsed) || parsed < 0) {
        walletModalError.value  = `El balance de ${currency} debe ser un número no negativo.`
        walletModalSaving.value = false
        return
      }

      const payload: WalletSetBalancePayload = { balance: rawValue }
      const res = await authStore.fetchWithAuth(`/api/wallets/${exchange}/${currency}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({})) as { detail?: string }
        walletModalError.value  = errData.detail ?? `Error ${res.status} al guardar ${currency}`
        walletModalSaving.value = false
        return
      }

      const updated = await res.json() as WalletSetBalanceResponse
      walletsStore.setBalances(
        walletsStore.balanceList.map((w) =>
          w.exchange === exchange && w.currency === currency
            ? { ...w, balance: updated.balance }
            : w,
        ),
      )
    }

    walletModalSuccess.value = true
    setTimeout(() => {
      walletModalVisible.value = false
      walletModalSuccess.value = false
    }, 1200)
  } catch (err) {
    walletModalError.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    walletModalSaving.value = false
  }
}

// ── Fee modal: funciones ──────────────────────────────────────────────────────
function openFeeModal(row: FeeRow): void {
  feeModalExchange.value = row.exchangeId
  // Convertir multiplicador a porcentaje para el formulario
  feeModalBuy.value      = feesStore.getFee(row.exchangeId, 'buy')  * 100
  feeModalSell.value     = feesStore.getFee(row.exchangeId, 'sell') * 100
  feeModalError.value    = null
  feeModalSuccess.value  = false
  feeModalVisible.value  = true
}

function closeFeeModal(): void {
  feeModalVisible.value = false
}

async function saveFeeModal(): Promise<void> {
  feeModalSaving.value  = true
  feeModalError.value   = null
  feeModalSuccess.value = false

  const buyVal  = feeModalBuy.value  ?? 0
  const sellVal = feeModalSell.value ?? 0

  try {
    await feesStore.updateFee(feeModalExchange.value, {
      fee_buy:  buyVal.toFixed(2),
      fee_sell: sellVal.toFixed(2),
    })
    feeModalSuccess.value = true
    setTimeout(() => {
      feeModalVisible.value = false
      feeModalSuccess.value = false
    }, 1200)
  } catch (err) {
    feeModalError.value = err instanceof Error ? err.message : 'Error al guardar comisiones'
  } finally {
    feeModalSaving.value = false
  }
}
</script>

<template>
  <div class="settings-view">
    <h1 class="settings-title">Configuración</h1>

    <div v-if="globalError" class="settings-error">{{ globalError }}</div>

    <!-- ── Sección: Modo Demo ─────────────────────────────────────────────── -->
    <MockModeCard />

    <!-- ── Sección: Control del Motor ─────────────────────────────────────── -->
    <BotControlCard />

    <!-- ── Sección: Exchanges ──────────────────────────────────────────── -->
    <section class="settings-section">
      <h2 class="settings-section-title">Exchanges</h2>
      <p class="settings-section-desc">
        Los exchanges marcados como <strong>Core</strong> no pueden desactivarse.
        Son necesarios para el funcionamiento del motor de arbitraje.
      </p>

      <div v-if="exchangesStore.isLoading" class="settings-loading">
        <ProgressSpinner style="width: 24px; height: 24px" />
        <span>Cargando exchanges...</span>
      </div>

      <div v-else-if="exchangesStore.error" class="settings-error">
        {{ exchangesStore.error }}
      </div>

      <div v-else class="exchanges-list">
        <div
          v-for="ex in exchangesStore.exchanges"
          :key="ex.exchange_id"
          class="exchange-row"
        >
          <div class="exchange-info">
            <span class="exchange-name">{{ ex.display_name }}</span>
            <span class="exchange-meta">{{ ex.currencies.join(' · ') }}</span>
          </div>
          <div class="exchange-controls">
            <Tag
              v-if="ex.core"
              value="Core"
              severity="info"
              class="exchange-core-badge"
            />
            <InputSwitch
              :model-value="ex.is_active"
              :disabled="ex.core"
              :title="ex.core ? 'Exchange core — no desactivable' : ''"
              @update:model-value="() => exchangesStore.toggleExchange(ex.exchange_id)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ── Sección: Parámetros de Capital ───────────────────────────────── -->
    <section class="settings-section">
      <h2 class="settings-section-title">Parámetros de Capital</h2>
      <p class="settings-section-desc">
        Configuración del monto operativo por transacción y umbral mínimo de
        rentabilidad para que el motor ejecute una oportunidad.
      </p>

      <div class="capital-display">
        <div class="capital-display-field">
          <span class="capital-display-label">Monto máx. por transacción</span>
          <span class="capital-display-value arb-mono">{{ configCapital.toFixed(2) }} USDT</span>
        </div>
        <div class="capital-display-field">
          <span class="capital-display-label">Umbral mín. profit</span>
          <span class="capital-display-value arb-mono">{{ configThreshold.toFixed(2) }} %</span>
        </div>
      </div>

      <div class="capital-edit-row">
        <Button
          label="Editar"
          size="small"
          severity="secondary"
          outlined
          :disabled="configStore.isLoading"
          @click="openConfigModal"
        />
      </div>
    </section>

    <!-- ── Sección: Wallets ────────────────────────────────────────────── -->
    <section class="settings-section">
      <h2 class="settings-section-title">Wallets</h2>
      <p class="settings-section-desc">
        Saldo de cada wallet simulada por exchange.
        Los cambios se reflejan en tiempo real en el Dashboard.
      </p>

      <div v-if="walletsStore.balanceList.length === 0" class="settings-loading">
        <ProgressSpinner style="width: 24px; height: 24px" />
        <span>Cargando wallets...</span>
      </div>

      <div v-else class="data-table-wrap">
        <div class="data-grid data-grid--header" style="grid-template-columns: 1.5fr 1fr 1.4fr 1fr 0.8fr">
          <div class="data-cell data-cell--header">Exchange</div>
          <div class="data-cell data-cell--header data-cell--right">USDT</div>
          <div class="data-cell data-cell--header data-cell--right">BTC</div>
          <div class="data-cell data-cell--header data-cell--right">ETH</div>
          <div class="data-cell data-cell--header data-cell--center">Editar</div>
        </div>
        <div
          v-for="row in walletRows"
          :key="row.exchangeId"
          class="data-grid data-grid--row"
          style="grid-template-columns: 1.5fr 1fr 1.4fr 1fr 0.8fr"
        >
          <div class="data-cell data-cell--name">{{ row.displayName }}</div>
          <div class="data-cell data-cell--right arb-mono">{{ row.usdt }}</div>
          <div class="data-cell data-cell--right arb-mono">{{ row.btc }}</div>
          <div class="data-cell data-cell--right arb-mono">{{ row.eth }}</div>
          <div class="data-cell data-cell--center">
            <Button
              label="Editar"
              size="small"
              severity="secondary"
              outlined
              @click="openWalletModal(row)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ── Sección: Comisiones ─────────────────────────────────────────── -->
    <section class="settings-section">
      <h2 class="settings-section-title">Comisiones</h2>
      <p class="settings-section-desc">
        Comisiones de compra y venta por exchange, expresadas en porcentaje.
        El motor de arbitraje usa estos valores para calcular el spread neto.
      </p>

      <div v-if="feesStore.loading" class="settings-loading">
        <ProgressSpinner style="width: 24px; height: 24px" />
        <span>Cargando comisiones...</span>
      </div>

      <div v-else-if="feesStore.error" class="settings-error">
        {{ feesStore.error }}
      </div>

      <div v-else class="data-table-wrap">
        <div class="data-grid data-grid--header" style="grid-template-columns: 1.5fr 1fr 1fr 0.8fr">
          <div class="data-cell data-cell--header">Exchange</div>
          <div class="data-cell data-cell--header data-cell--right">Fee Compra</div>
          <div class="data-cell data-cell--header data-cell--right">Fee Venta</div>
          <div class="data-cell data-cell--header data-cell--center">Editar</div>
        </div>
        <div
          v-for="row in feeRows"
          :key="row.exchangeId"
          class="data-grid data-grid--row"
          style="grid-template-columns: 1.5fr 1fr 1fr 0.8fr"
        >
          <div class="data-cell data-cell--name">{{ row.displayName }}</div>
          <div class="data-cell data-cell--right arb-mono">{{ row.feeBuyDisplay }}</div>
          <div class="data-cell data-cell--right arb-mono">{{ row.feeSellDisplay }}</div>
          <div class="data-cell data-cell--center">
            <Button
              label="Editar"
              size="small"
              severity="secondary"
              outlined
              @click="openFeeModal(row)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ── Modal: Editar wallets ───────────────────────────────────────── -->
    <Dialog
      v-model:visible="walletModalVisible"
      :header="walletModalTitle"
      modal
      :closable="!walletModalSaving"
      :style="{ width: '400px' }"
      @hide="closeWalletModal"
    >
      <div class="modal-body">
        <div
          v-for="currency in CURRENCIES"
          :key="currency"
          class="modal-field"
        >
          <label class="modal-label">{{ currency }}</label>
          <div class="modal-controls">
            <Button
              icon="pi pi-minus"
              size="small"
              severity="secondary"
              outlined
              :disabled="walletModalSaving"
              @click="adjustBalance(currency, -1)"
            />
            <InputText
              v-model="walletModalInputs[currency]"
              class="modal-input arb-mono"
              :disabled="walletModalSaving"
              @blur="formatOnBlur(currency)"
            />
            <Button
              icon="pi pi-plus"
              size="small"
              severity="secondary"
              outlined
              :disabled="walletModalSaving"
              @click="adjustBalance(currency, 1)"
            />
          </div>
          <div class="modal-hint">
            <span v-if="currency === 'USDT'">± 100 USDT · mín. 0.00</span>
            <span v-else-if="currency === 'BTC'">± 0.00000001 BTC · mín. 0.00000000</span>
            <span v-else>± 0.0000001 ETH · mín. 0.0000000</span>
          </div>
        </div>

        <div v-if="walletModalError" class="modal-feedback modal-feedback--error">
          {{ walletModalError }}
        </div>
        <div v-else-if="walletModalSuccess" class="modal-feedback modal-feedback--success">
          Wallets actualizadas correctamente.
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          outlined
          :disabled="walletModalSaving"
          @click="closeWalletModal"
        />
        <Button
          label="Guardar"
          :loading="walletModalSaving"
          :disabled="walletModalSaving"
          @click="saveWalletModal"
        />
      </template>
    </Dialog>

    <!-- ── Modal: Editar parámetros de capital ───────────────────────── -->
    <Dialog
      v-model:visible="configModalVisible"
      header="Editar Parámetros de Capital"
      modal
      :closable="!configModalSaving"
      :style="{ width: '400px' }"
      @hide="closeConfigModal"
    >
      <div class="modal-body">
        <div class="modal-field">
          <label class="modal-label">Monto máximo por transacción (USDT)</label>
          <InputNumber
            v-model="configModalCapital"
            :min="100"
            :max="1000000"
            :step="100"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            mode="decimal"
            :disabled="configModalSaving"
            class="config-modal-input"
          />
          <div class="modal-hint">
            Rango: <span class="arb-mono">100</span> –
            <span class="arb-mono">1,000,000</span> USDT · step: 100
          </div>
        </div>

        <div class="modal-field">
          <label class="modal-label">Umbral mínimo de profit (ROI %)</label>
          <InputNumber
            v-model="configModalThreshold"
            :min="0.01"
            :max="100"
            :step="0.01"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            suffix=" %"
            :disabled="configModalSaving"
            class="config-modal-input"
          />
          <div class="modal-hint">
            Rango: <span class="arb-mono">0.01%</span> –
            <span class="arb-mono">100.00%</span> · step: 0.01
          </div>
        </div>

        <div v-if="configModalError" class="modal-feedback modal-feedback--error">
          {{ configModalError }}
        </div>
        <div v-else-if="configModalSuccess" class="modal-feedback modal-feedback--success">
          Configuración guardada
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          outlined
          :disabled="configModalSaving"
          @click="closeConfigModal"
        />
        <Button
          label="Guardar"
          :loading="configModalSaving"
          :disabled="configModalSaving"
          @click="saveConfigModal"
        />
      </template>
    </Dialog>

    <!-- ── Modal: Editar comisiones ───────────────────────────────────── -->
    <Dialog
      v-model:visible="feeModalVisible"
      :header="feeModalTitle"
      modal
      :closable="!feeModalSaving"
      :style="{ width: '380px' }"
      @hide="closeFeeModal"
    >
      <div class="modal-body">
        <div class="modal-field">
          <label class="modal-label">Fee Compra (%)</label>
          <InputNumber
            v-model="feeModalBuy"
            :min="0"
            :max="9.99"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            :disabled="feeModalSaving"
            :step="0.01"
            class="fee-modal-input"
          />
          <div class="modal-hint">Rango: 0.00% – 9.99%</div>
        </div>

        <div class="modal-field">
          <label class="modal-label">Fee Venta (%)</label>
          <InputNumber
            v-model="feeModalSell"
            :min="0"
            :max="9.99"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            :disabled="feeModalSaving"
            :step="0.01"
            class="fee-modal-input"
          />
          <div class="modal-hint">Rango: 0.00% – 9.99%</div>
        </div>

        <div v-if="feeModalError" class="modal-feedback modal-feedback--error">
          {{ feeModalError }}
        </div>
        <div v-else-if="feeModalSuccess" class="modal-feedback modal-feedback--success">
          Comisiones actualizadas correctamente.
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          outlined
          :disabled="feeModalSaving"
          @click="closeFeeModal"
        />
        <Button
          label="Guardar"
          :loading="feeModalSaving"
          :disabled="feeModalSaving"
          @click="saveFeeModal"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.settings-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--arb-text-primary);
  margin: 0 0 0.5rem;
}

.settings-section {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.settings-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--arb-text-primary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.settings-section-desc {
  font-size: 0.85rem;
  color: var(--arb-text-secondary);
  margin: 0;
}

.settings-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--arb-text-muted);
  font-size: 0.85rem;
}

.settings-error {
  color: var(--arb-loss, #ff4757);
  font-size: 0.875rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

/* ── Exchanges ─── */
.exchanges-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.exchange-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--arb-border);
}

.exchange-row:last-child { border-bottom: none; }

.exchange-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.exchange-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--arb-text-primary);
}

.exchange-meta {
  font-size: 0.78rem;
  color: var(--arb-text-muted);
}

.exchange-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.exchange-core-badge { font-size: 0.7rem; }

/* ── Tabla genérica (wallets + fees) ─── */
.data-table-wrap {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--arb-border);
  border-radius: 6px;
  overflow: hidden;
}

.data-grid {
  display: grid;
  align-items: center;
}

.data-grid--header {
  background: var(--arb-bg-elevated, rgba(255,255,255,0.03));
  border-bottom: 1px solid var(--arb-border);
}

.data-grid--row {
  border-bottom: 1px solid var(--arb-border);
  transition: background 0.15s;
}

.data-grid--row:last-child { border-bottom: none; }

.data-grid--row:hover {
  background: var(--arb-bg-elevated, rgba(255,255,255,0.02));
}

.data-cell {
  padding: 0.6rem 0.75rem;
  font-size: 0.85rem;
  color: var(--arb-text-primary);
}

.data-cell--header {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-cell--name  { font-weight: 600; }
.data-cell--right { text-align: right; }
.data-cell--center { text-align: center; }

/* ── Modal compartido ─── */
.modal-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.25rem 0;
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.modal-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--arb-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.modal-hint {
  font-size: 0.74rem;
  color: var(--arb-text-muted);
}

.modal-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.modal-input {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 0.95rem;
  font-weight: 600;
}

/* Centra el texto dentro del InputText de PrimeVue */
.modal-input :deep(input) {
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.95rem;
  font-weight: 600;
  width: 100%;
}

.modal-feedback {
  font-size: 0.82rem;
  border-radius: 5px;
  padding: 0.5rem 0.75rem;
}

.modal-feedback--error {
  color: var(--arb-loss, #ff4757);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.modal-feedback--success {
  color: var(--arb-profit, #00d4aa);
  background: rgba(0, 212, 170, 0.08);
  border: 1px solid rgba(0, 212, 170, 0.25);
}

.fee-modal-input {
  width: 100%;
}

/* ── Capital display ─── */
.capital-display {
  display: flex;
  gap: 2rem;
}

.capital-display-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.capital-display-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--arb-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.capital-display-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--arb-text-primary);
}

.capital-edit-row {
  display: flex;
  justify-content: flex-end;
}

.config-modal-input {
  width: 100%;
}
</style>
