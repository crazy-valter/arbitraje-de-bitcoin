/**
 * useFormatCurrency — formateo consistente de valores financieros.
 *
 * Siempre usar este composable, nunca formatear inline en los templates.
 */

export function useFormatCurrency() {
  /**
   * Formatea un valor P&L en USDT con signo.
   * Ejemplos: "1247.83" → "+$1,247.83" | "-21.62" → "-$21.62"
   */
  function formatUSDT(value: string | number): string {
    const n = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(n)) return '$0.00'
    const sign = n >= 0 ? '+' : ''
    return `${sign}$${Math.abs(n).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  /**
   * Formatea un balance en USDT sin signo — para wallets.
   * Ejemplo: "14200" → "$14,200.00"
   */
  function formatUSDTPlain(value: string | number): string {
    const n = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(n)) return '$0.00'
    return `$${n.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  /**
   * Formatea un valor en BTC con 5 decimales.
   * Ejemplo: "0.38412" → "0.38412 BTC"
   */
  function formatBTC(value: string | number): string {
    const n = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(n)) return '0.00000000 BTC'
    return `${n.toFixed(8)} BTC`
  }

  /**
   * Formatea un porcentaje con signo y 3 decimales.
   * Ejemplos: "0.18" → "+0.180%" | "-0.05" → "-0.050%"
   */
  function formatPct(value: string | number): string {
    const n = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(n)) return '0.000%'
    const sign = n >= 0 ? '+' : ''
    return `${sign}${n.toFixed(3)}%`
  }

  /**
   * Formatea un score numérico con 3 decimales.
   * Ejemplo: 0.873 → "0.873"
   */
  function formatScore(value: number): string {
    return value.toFixed(3)
  }

  /**
   * Formatea un número grande con separadores de miles.
   * Ejemplo: 1247834.5 → "1,247,834.50"
   */
  function formatNumber(value: number, decimals = 2): string {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value)
  }

  return {
    formatUSDT,
    formatUSDTPlain,
    formatBTC,
    formatPct,
    formatScore,
    formatNumber,
  }
}
