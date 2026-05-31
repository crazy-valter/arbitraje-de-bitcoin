// Tipos del dominio — interfaces TypeScript completas para el sistema de arbitraje

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface User {
  email: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  ok: boolean
  user: User
  expires_at: string
}

// ── Order Books ───────────────────────────────────────────────────────────────

export interface OrderBookUpdate {
  type: 'orderbook_update'
  exchange: string
  ask: string     // Decimal serializado como string
  bid: string     // Decimal serializado como string
  timestamp: string
}

export interface ExchangeOrderBook {
  exchange: string
  ask: string
  bid: string
  timestamp: string
  isStale: boolean
}

// ── Opportunities ─────────────────────────────────────────────────────────────

export type OpportunityStatus = 'DETECTED' | 'EXECUTING' | 'EXECUTED' | 'REJECTED' | 'FAILED'
export type Strategy = 'cross_exchange' | 'triangular' | 'statistical'

export interface ArbitrageOpportunity {
  id: string
  buyExchange: string
  sellExchange: string
  buyPrice: string
  sellPrice: string
  grossSpreadPct: string
  totalFeesUsdt: string
  slippageUsdt: string
  netProfitUsdt: string
  netProfitPct: string
  maxVolumeBtc: string
  strategy: Strategy
  score: number
  status: OpportunityStatus
  detectedAt: string
  executedAt: string | null
  // Desglose de fees (CHG-009)
  tradingFeeBuyUsdt: string
  tradingFeeSellUsdt: string
  withdrawalFeeUsdt: string
  networkLatencyMs: string
}

// Formato del evento SSE (snake_case del backend)
export interface OpportunityEvent {
  type: 'opportunity'
  id: string
  buy_exchange: string
  sell_exchange: string
  buy_price: string
  sell_price: string
  gross_spread_pct: string
  total_fees_usdt: string
  slippage_usdt: string
  net_profit_usdt: string
  net_profit_pct: string
  max_volume_btc: string
  strategy: Strategy
  score: number
  status: OpportunityStatus
  detected_at: string
  // Desglose de fees (CHG-009)
  trading_fee_buy_usdt?: string
  trading_fee_sell_usdt?: string
  withdrawal_fee_usdt?: string
  network_latency_ms?: string
}

// ── Trades ────────────────────────────────────────────────────────────────────

export type TradeSide = 'BUY' | 'SELL'

export interface SimulatedTrade {
  id: string
  opportunityId: string
  side: TradeSide
  exchange: string
  price: string
  volumeBtc: string
  feeUsdt: string
  slippageUsdt: string
  executedAt: string
  isPartial: boolean
  status: string
  // Wallet snapshot (CHG-009)
  walletUsdtBefore: string
  walletUsdtAfter: string
  walletBtcBefore: string
  walletBtcAfter: string
}

export interface TradeExecutedEvent {
  type: 'trade_simulated'
  opportunity_id: string
  net_profit_usdt: string
  net_profit_pct: string
  buy_exchange: string
  sell_exchange: string
  status: string
}

// ── Wallets ───────────────────────────────────────────────────────────────────

export interface WalletBalance {
  exchange: string
  currency: string
  balance: string
  updatedAt: string | null
}

export interface WalletUpdateEvent {
  type: 'wallet_update'
  exchange: string
  currency: string
  balance: string
  timestamp: string
}

// ── Metrics ───────────────────────────────────────────────────────────────────

export interface SystemMetrics {
  opportunitiesTotal: number
  executedTotal: number
  winRatePct: number
  totalPnlUsdt: number
  connectedExchanges: number
  exchangeLatencies: Record<string, number>
  uptimeSeconds: number
  timestamp: string
}

export interface MetricsUpdateEvent {
  type: 'metrics_update'
  opportunities_detected: number
  trades_simulated: number
  win_rate_pct: number
  total_pnl_usdt: number
  connected_exchanges: number
  exchange_latencies: Record<string, number>
  uptime_seconds: number
  timestamp: string
}

// ── Config ────────────────────────────────────────────────────────────────────

export interface BotConfig {
  initialCapitalUsdt: string
  minProfitThresholdPct: string
  strategyCrossExchange: boolean
  strategyTriangular: boolean
  strategyStatistical: boolean
  mockModeEnabled: boolean
}

export interface ConfigUpdatePayload {
  initial_capital_usdt?: string
  min_profit_threshold_pct?: string
  strategy_cross_exchange?: boolean
  strategy_triangular?: boolean
  strategy_statistical?: boolean
  mock_mode_enabled?: boolean
}

// ── Exchanges ─────────────────────────────────────────────────────────────────

export interface ExchangeInfo {
  exchange_id: string
  display_name: string
  currencies: string[]
  fees_taker: string   // Decimal serializado como string
  core: boolean
  is_active: boolean
}

// ── Wallet (set balance) ──────────────────────────────────────────────────────

export interface WalletSetBalancePayload {
  balance: string      // Decimal serializado como string
}

export interface WalletSetBalanceResponse {
  exchange: string
  currency: string
  balance: string
  updated: boolean
}

// ── Fees ──────────────────────────────────────────────────────────────────────

export interface ExchangeFeeInfo {
  exchange_id: string
  display_name: string
  fee_buy: string   // multiplicador como string, ej. "0.001" = 0.1%
  fee_sell: string
}

export interface ExchangeFeeUpdatePayload {
  fee_buy: string   // porcentaje como string, ej. "0.10" = 0.10%
  fee_sell: string
}

// ── SSE Events (union type) ───────────────────────────────────────────────────

export type SSEEvent =
  | OrderBookUpdate
  | OpportunityEvent
  | TradeExecutedEvent
  | WalletUpdateEvent
  | MetricsUpdateEvent

// ── Paginación y filtros (CHG-009) ────────────────────────────────────────────

export interface PaginatedOpportunitiesResponse {
  items: ArbitrageOpportunity[]
  total: number
}

export interface OpportunityFilters {
  status?: OpportunityStatus[]
  buyExchange?: string[]
  sellExchange?: string[]
  fromDt?: string | null
  toDt?: string | null
}
