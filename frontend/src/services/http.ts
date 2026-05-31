/**
 * createFetchWithAuth — interceptor HTTP con cola de 401 y refresh automático.
 *
 * Si una petición recibe 401:
 * 1. Intenta refresh del token (POST /api/auth/refresh, credentials: include)
 * 2. Si el refresh tiene éxito, reintenta todas las peticiones en cola
 * 3. Si el refresh falla, llama a logout() y rechaza todas las peticiones en cola
 *
 * El singleton garantiza que solo un refresh se ejecuta a la vez aunque
 * múltiples peticiones fallen con 401 simultáneamente.
 */

type PendingRequest = {
  retry: () => void
  abort: (e: Error) => void
}

const REFRESH_TIMEOUT_MS = 10_000

async function tryRefresh(): Promise<boolean> {
  const ctrl = new AbortController()
  const tid = setTimeout(() => ctrl.abort(), REFRESH_TIMEOUT_MS)
  try {
    const r = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      signal: ctrl.signal,
    })
    return r.ok
  } catch {
    return false
  } finally {
    clearTimeout(tid)
  }
}

export function createFetchWithAuth(logout: () => void) {
  let isRefreshing = false
  const pending: PendingRequest[] = []

  return async function fetchWithAuth(
    url: string,
    opts: RequestInit = {},
  ): Promise<Response> {
    const res = await fetch(url, { ...opts, credentials: 'include' })

    // Si no es 401, retornar la respuesta directamente
    if (res.status !== 401) return res

    // Si ya hay un refresh en curso, encolar esta petición
    if (isRefreshing) {
      return new Promise<Response>((resolve, reject) => {
        pending.push({
          retry: () => resolve(fetch(url, { ...opts, credentials: 'include' })),
          abort: (e) => reject(e),
        })
      })
    }

    // Iniciar el refresh
    isRefreshing = true
    let refreshed = false
    try {
      refreshed = await tryRefresh()
    } finally {
      isRefreshing = false
    }

    const queue = [...pending]
    pending.length = 0

    if (refreshed) {
      // Refresh exitoso: reintentar todas las peticiones en cola
      queue.forEach(({ retry }) => retry())
      return fetch(url, { ...opts, credentials: 'include' })
    } else {
      // Refresh fallido: abortar todas y hacer logout
      queue.forEach(({ abort }) => abort(new Error('Sesión expirada')))
      logout()
      return res
    }
  }
}
