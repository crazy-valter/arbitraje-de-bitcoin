/**
 * useRelativeTime — timestamps relativos para la UI.
 * Ejemplo: "2024-01-15T14:23:01Z" → "hace 3s"
 */

export function useRelativeTime() {
  function relativeTime(isoString: string): string {
    const diff = Date.now() - new Date(isoString).getTime()
    if (diff < 60_000) return `hace ${Math.floor(diff / 1_000)}s`
    if (diff < 3_600_000) return `hace ${Math.floor(diff / 60_000)}m`
    return `hace ${Math.floor(diff / 3_600_000)}h`
  }

  return { relativeTime }
}
