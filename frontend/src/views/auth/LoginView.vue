<script setup lang="ts">
// 1. Imports
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useSSE } from '@/composables/useSSE'
import { usePublicPrices } from '@/composables/usePublicPrices'
import { useFormatCurrency } from '@/composables/useFormatCurrency'

// 2. Stores & composables
const router = useRouter()
const auth = useAuthStore()
const { connect } = useSSE()
const { prices } = usePublicPrices()
const { formatUSDTPlain } = useFormatCurrency()

// 3. State local
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMsg = ref('')

// 4. Computed — datos de exchanges para el panel izquierdo
const EXCHANGE_ORDER = ['binance', 'kraken', 'bybit'] as const

type ExchangeKey = (typeof EXCHANGE_ORDER)[number]

const EXCHANGE_LABELS: Record<ExchangeKey, string> = {
  binance: 'Binance',
  kraken: 'Kraken',
  bybit: 'Bybit',
}

const EXCHANGE_COLORS: Record<ExchangeKey, string> = {
  binance: 'var(--arb-binance)',
  kraken: 'var(--arb-kraken)',
  bybit: 'var(--arb-bybit)',
}

// Sparkline SVG polyline points — decorativos, distintos por exchange
const SPARKLINE_POINTS: Record<ExchangeKey, string> = {
  binance: '0,20 8,16 16,18 24,10 32,12 40,6 52,4', // alcista
  kraken: '0,8 8,12 16,10 24,16 32,14 40,18 52,16', // bajista
  bybit: '0,18 8,14 16,16 24,8 32,10 40,4 52,6', // alcista
}

const exchangeItems = computed(() =>
  EXCHANGE_ORDER.map((key) => {
    const data = prices.value.find((p) => p.exchange === key)
    return {
      key,
      label: EXCHANGE_LABELS[key],
      color: EXCHANGE_COLORS[key],
      points: SPARKLINE_POINTS[key],
      price: data ? formatUSDTPlain(data.ask) : '—', // — guion largo
      isStale: data ? data.is_stale : true,
    }
  }),
)

// Spread máximo entre exchanges con datos no-stale
const maxSpread = computed(() => {
  const active = prices.value.filter((p) => !p.is_stale)
  if (active.length < 2) return '—'
  const bids = active.map((p) => parseFloat(p.bid))
  const asks = active.map((p) => parseFloat(p.ask))
  const maxBid = Math.max(...bids)
  const minAsk = Math.min(...asks)
  const spread = ((maxBid - minAsk) / minAsk) * 100
  return `${spread.toFixed(3)}%`
})

// Exchanges activos (no stale)
const activeExchanges = computed(() => {
  const count = prices.value.filter((p) => !p.is_stale).length
  return count > 0 ? `${count} activos` : '—'
})

// 8. Handlers
async function handleLogin(): Promise<void> {
  if (!email.value || !password.value) {
    errorMsg.value = 'Ingresa email y contraseña'
    return
  }
  isLoading.value = true
  errorMsg.value = ''
  try {
    await auth.login(email.value, password.value)
    connect()
    await router.push({ name: 'dashboard' })
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : 'Error al iniciar sesión'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="cx-page">
    <div class="cx-card">
      <!-- Panel Izquierdo — Mercados en vivo -->
      <aside class="cx-left">
        <div class="cx-left__decor cx-left__decor--before" />
        <div class="cx-left__decor cx-left__decor--after" />

        <!-- Logo -->
        <div class="cx-logo">
          <span class="cx-logo__icon">
            <i class="pi pi-bitcoin" />
          </span>
          <span class="cx-logo__text">ArbitrageBot</span>
        </div>

        <!-- Label -->
        <p class="cx-market-label">Mercados en vivo</p>

        <!-- Tickers -->
        <div class="cx-tickers">
          <div
            v-for="item in exchangeItems"
            :key="item.key"
            class="cx-ticker"
            :class="['cx-ticker--' + item.key, { 'cx-ticker--stale': item.isStale }]"
          >
            <div class="cx-ticker__header">
              <span class="cx-ticker__dot" />
              <span class="cx-ticker__name">{{ item.label }}</span>
              <span class="cx-ticker__pair">BTC/USDT</span>
            </div>
            <!-- Sparkline SVG decorativo -->
            <svg
              class="cx-ticker__sparkline"
              viewBox="0 0 52 24"
              preserveAspectRatio="none"
            >
              <polyline
                :points="item.points"
                fill="none"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                :stroke="item.isStale ? 'var(--arb-text-muted)' : item.color"
              />
            </svg>
            <span class="cx-ticker__price arb-mono">{{ item.price }}</span>
          </div>
        </div>

        <!-- Footer stats -->
        <div class="cx-left__divider" />
        <div class="cx-stats">
          <div class="cx-stat">
            <span class="cx-stat__label">Spread max</span>
            <span class="cx-stat__value arb-mono">{{ maxSpread }}</span>
          </div>
          <div class="cx-stat">
            <span class="cx-stat__label">Exchanges</span>
            <span class="cx-stat__value arb-mono">{{ activeExchanges }}</span>
          </div>
        </div>
      </aside>

      <!-- Panel Derecho — Login -->
      <main class="cx-right">
        <!-- Badge sistema activo -->
        <div class="cx-badge">
          <span class="cx-badge__dot" />
          <span class="cx-badge__text">Sistema activo</span>
          <span class="cx-badge__sep">&middot;</span>
          <span class="cx-badge__brand">ArbitrageBot</span>
        </div>

        <!-- Heading -->
        <h1 class="cx-heading">
          Bienvenido de<br />vuelta al sistema
        </h1>
        <p class="cx-subheading">Accede para gestionar el bot de arbitraje.</p>

        <!-- Formulario -->
        <form class="cx-form" @submit.prevent="handleLogin">
          <div class="cx-input-wrapper">
            <i class="pi pi-envelope cx-input-icon" />
            <InputText
              v-model="email"
              type="email"
              placeholder="Email"
              :disabled="isLoading"
              autocomplete="username"
              class="cx-input"
            />
          </div>

          <div class="cx-input-wrapper">
            <i class="pi pi-lock cx-input-icon" />
            <Password
              v-model="password"
              placeholder="Contraseña"
              :disabled="isLoading"
              :feedback="false"
              :toggle-mask="true"
              autocomplete="current-password"
              fluid
              class="cx-input"
            />
          </div>

          <Message
            v-if="errorMsg"
            severity="error"
            :closable="false"
            class="cx-error"
          >
            {{ errorMsg }}
          </Message>

          <Button
            type="submit"
            label="Iniciar sesión"
            :loading="isLoading"
            icon="pi pi-arrow-right"
            icon-pos="right"
            class="cx-submit"
          />
        </form>

        <!-- Divider decorativo -->
        <div class="cx-divider">
          <span class="cx-divider__line" />
          <span class="cx-divider__text">Acceso seguro</span>
          <span class="cx-divider__line" />
        </div>

        <!-- Footer -->
        <div class="cx-footer">
          <i class="pi pi-shield" />
          <span>2FA disponible</span>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ──────────────────────────────────── Page ───────────────────────────────── */
.cx-page {
  min-height: 100vh;
  min-width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--arb-bg-base);
  padding: 1.5rem;
}

/* ──────────────────────────────────── Card ───────────────────────────────── */
.cx-card {
  display: flex;
  width: 100%;
  max-width: 920px;
  min-height: 560px;
  border-radius: 24px;
  overflow: hidden;
  border: 1px solid var(--arb-border);
}

/* ─────────────────────────────── Panel Izquierdo ─────────────────────────── */
.cx-left {
  position: relative;
  width: 340px;
  flex-shrink: 0;
  background: var(--arb-bg-base);
  padding: 2.5rem 2rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Blobs decorativos */
.cx-left__decor {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.cx-left__decor--before {
  top: -60px;
  left: -60px;
  width: 200px;
  height: 200px;
  background: rgba(0, 212, 170, 0.10);
}

.cx-left__decor--after {
  bottom: -40px;
  right: -40px;
  width: 160px;
  height: 160px;
  background: rgba(0, 212, 170, 0.07);
}

/* Logo */
.cx-logo {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.cx-logo__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 8px;
  background: var(--arb-accent-primary);
  color: #fff;
  font-size: 1.1rem;
}

.cx-logo__text {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--arb-text-primary);
}

/* Market label */
.cx-market-label {
  position: relative;
  z-index: 1;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--arb-text-muted);
  margin-bottom: 1rem;
}

/* Tickers */
.cx-tickers {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cx-ticker {
  padding: 0.75rem;
  border-radius: 10px;
  background: var(--arb-bg-elevated);
  border: 1px solid var(--arb-border);
}

.cx-ticker__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.cx-ticker__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Color del dot según exchange — tokens específicos */
.cx-ticker--binance .cx-ticker__dot { background: var(--arb-binance); }
.cx-ticker--kraken .cx-ticker__dot  { background: var(--arb-kraken); }
.cx-ticker--bybit .cx-ticker__dot   { background: var(--arb-bybit); }

/* Stale va después para ganar la cascada */
.cx-ticker--stale .cx-ticker__dot {
  background: var(--arb-loss);
}

.cx-ticker__name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--arb-text-primary);
}

.cx-ticker__pair {
  font-size: 0.6875rem;
  color: var(--arb-text-muted);
  margin-left: auto;
}

.cx-ticker__sparkline {
  display: block;
  width: 100%;
  height: 20px;
  margin-bottom: 0.375rem;
  opacity: 0.7;
}

.cx-ticker--stale .cx-ticker__sparkline {
  opacity: 0.35;
}

.cx-ticker__price {
  display: block;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--arb-text-primary);
}

/* Divider */
.cx-left__divider {
  position: relative;
  z-index: 1;
  height: 1px;
  background: var(--arb-border);
  margin: 1.25rem 0 1rem;
}

/* Stats */
.cx-stats {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 0.75rem;
}

.cx-stat {
  flex: 1;
  padding: 0.625rem 0.75rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.cx-stat__label {
  display: block;
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--arb-text-muted);
  margin-bottom: 0.25rem;
}

.cx-stat__value {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--arb-text-primary);
}

/* ─────────────────────────────── Panel Derecho ───────────────────────────── */
.cx-right {
  flex: 1;
  background: var(--arb-bg-surface);
  padding: 2.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* Badge sistema activo */
.cx-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 999px;
  background: rgba(0, 212, 170, 0.08);
  border: 0.5px solid rgba(0, 212, 170, 0.25);
  margin-bottom: 2rem;
  width: fit-content;
}

.cx-badge__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--arb-accent-primary);
  animation: cx-pulse 2s infinite;
}

.cx-badge__text {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--arb-accent-primary);
}

.cx-badge__sep {
  font-size: 0.75rem;
  color: var(--arb-text-muted);
}

.cx-badge__brand {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--arb-text-secondary);
}

@keyframes cx-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}

/* Heading */
.cx-heading {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--arb-text-primary);
  margin: 0 0 0.5rem;
  line-height: 1.3;
}

.cx-subheading {
  font-size: 0.9375rem;
  color: var(--arb-text-secondary);
  margin: 0 0 2rem;
}

/* Form */
.cx-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Input wrapper con icono prefix */
.cx-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.cx-input-icon {
  position: absolute;
  left: 1rem;
  font-size: 0.875rem;
  color: var(--arb-text-muted);
  z-index: 1;
  pointer-events: none;
}

.cx-input {
  width: 100%;
}

/* Override PrimeVue InputText dentro del wrapper para dar padding al icono */
.cx-input-wrapper :deep(.cx-input input.p-inputtext),
.cx-input-wrapper :deep(input.p-inputtext.cx-input) {
  padding-left: 2.75rem;
}

/* PrimeVue Password wrapper alignment */
.cx-input-wrapper :deep(.p-password) {
  width: 100%;
}

.cx-input-wrapper :deep(.p-password-input) {
  padding-left: 2.75rem;
}

/* Error */
.cx-error {
  margin: 0;
}

/* Submit — override PrimeVue Aura primary color con design tokens del sistema */
.cx-submit {
  margin-top: 0.5rem;
  --p-button-primary-background: var(--arb-accent-primary);
  --p-button-primary-hover-background: var(--arb-accent-hover);
  --p-button-primary-active-background: var(--arb-accent-hover);
  --p-button-primary-border-color: var(--arb-accent-primary);
  --p-button-primary-hover-border-color: var(--arb-accent-hover);
  --p-button-primary-active-border-color: var(--arb-accent-hover);
}

/* Divider decorativo */
.cx-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.75rem;
  margin-bottom: 1rem;
}

.cx-divider__line {
  flex: 1;
  height: 1px;
  background: var(--arb-border);
}

.cx-divider__text {
  font-size: 0.6875rem;
  color: var(--arb-text-muted);
  white-space: nowrap;
}

/* Footer */
.cx-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--arb-text-muted);
}

.cx-footer i {
  font-size: 0.875rem;
}

/* ──────────────────────────────── Responsive ─────────────────────────────── */
@media (max-width: 640px) {
  .cx-left {
    display: none;
  }

  .cx-card {
    border-radius: 20px;
  }

  .cx-right {
    padding: 2rem 1.5rem;
  }

  .cx-heading {
    font-size: 1.375rem;
  }
}
</style>
