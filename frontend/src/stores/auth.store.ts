/**
 * Auth Store — gestiona la sesión del operador.
 *
 * - Los tokens viajan SOLO como cookies HttpOnly (el frontend nunca los lee)
 * - sessionStorage guarda solo datos de UI: email y expires_at
 * - scheduleRefresh: renueva el token 3 minutos antes de expirar
 * - fetchWithAuth: cola de 401 + refresh automático
 */

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { User } from '@/types'
import { createFetchWithAuth } from '@/services/http'

function loadUserFromSession(): User | null {
  const raw = sessionStorage.getItem('auth_user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(loadUserFromSession())
  const expiresAt = ref<string | null>(sessionStorage.getItem('auth_expires_at'))
  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  const isAuthenticated = computed(() => user.value !== null)

  // Crear fetchWithAuth con acceso al logout para el caso de refresh fallido
  const fetchWithAuth = createFetchWithAuth(() => logout())

  function scheduleRefresh(expires: string): void {
    if (refreshTimer) clearTimeout(refreshTimer)
    // Renovar 3 minutos antes de que expire
    const delay = new Date(expires).getTime() - Date.now() - 3 * 60 * 1000
    if (delay <= 0) {
      // Ya expiró o está a punto de hacerlo — renovar inmediatamente
      void doRefresh()
      return
    }
    refreshTimer = setTimeout(() => void doRefresh(), delay)
  }

  async function doRefresh(): Promise<void> {
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json() as { ok: boolean; expires_at: string }
        expiresAt.value = data.expires_at
        sessionStorage.setItem('auth_expires_at', data.expires_at)
        scheduleRefresh(data.expires_at)
      } else {
        await logout()
      }
    } catch {
      // Error de red — no hacer logout inmediatamente, dejar que el interceptor lo maneje
    }
  }

  async function login(email: string, password: string): Promise<User> {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({})) as { detail?: string }
      throw new Error(data.detail ?? 'Credenciales inválidas')
    }

    const data = await res.json() as {
      ok: boolean
      user: User
      expires_at: string
    }

    user.value = data.user
    expiresAt.value = data.expires_at
    sessionStorage.setItem('auth_user', JSON.stringify(data.user))
    sessionStorage.setItem('auth_expires_at', data.expires_at)
    scheduleRefresh(data.expires_at)

    return data.user
  }

  async function logout(): Promise<void> {
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    } catch {
      // Ignorar errores de red al salir
    }
    user.value = null
    expiresAt.value = null
    sessionStorage.removeItem('auth_user')
    sessionStorage.removeItem('auth_expires_at')
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
  }

  // Reanudar refresh automático si hay sesión guardada
  if (expiresAt.value) {
    scheduleRefresh(expiresAt.value)
  }

  return {
    user,
    isAuthenticated,
    expiresAt,
    fetchWithAuth,
    login,
    logout,
    scheduleRefresh,
  }
})
