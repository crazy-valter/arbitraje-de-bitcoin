<script setup lang="ts">
// Imports
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useConfigStore } from '@/stores/config.store'
import SseStatusIndicator from '@/components/common/SseStatusIndicator.vue'

// Stores
const authStore = useAuthStore()
const configStore = useConfigStore()
const router = useRouter()

// State local
const isLoggingOut = ref(false)

// Items de navegación — la propiedad route activa el router-link-active de PrimeVue
const navItems = [
  { label: 'Dashboard',     icon: 'pi pi-chart-line', route: '/' },
  { label: 'Transacciones', icon: 'pi pi-list',       route: '/transactions' },
  { label: 'Configuración', icon: 'pi pi-cog',        route: '/settings' },
]

// Cargar config al montar el layout para que el banner esté disponible en todas las vistas
onMounted(async () => {
  await configStore.fetchConfig()
})

// Handlers
async function handleLogout(): Promise<void> {
  isLoggingOut.value = true
  await authStore.logout()
  await router.push({ name: 'login' })
  isLoggingOut.value = false
}
</script>

<template>
  <div class="arb-shell">
    <Menubar :model="navItems" class="arb-menubar">
      <template #start>
        <span class="arb-brand">
          <i class="pi pi-bitcoin" />
          ArbitrageBot
        </span>
      </template>
      <template #item="{ item, props }">
        <router-link
          v-if="item.route"
          v-slot="{ href, navigate, isExactActive }"
          :to="item.route"
          custom
        >
          <a
            v-bind="props.action"
            :href="href"
            :class="{ 'arb-nav-active': isExactActive }"
            @click="navigate"
          >
            <span :class="item.icon" />
            <span class="arb-nav-label">{{ item.label }}</span>
          </a>
        </router-link>
      </template>
      <template #end>
        <div class="arb-menubar-end">
          <SseStatusIndicator />
          <Button
            label="Salir"
            text
            size="small"
            icon="pi pi-sign-out"
            :disabled="isLoggingOut"
            @click="handleLogout"
          />
        </div>
      </template>
    </Menubar>
    <!-- Banner global Modo Demo — visible en todas las vistas cuando está activo -->
    <div v-if="configStore.config.mockModeEnabled" class="arb-demo-banner">
      <i class="pi pi-exclamation-triangle arb-demo-banner__icon" />
      <span>
        <strong>Modo Demo activo</strong> — el sistema no está conectado a exchanges reales.
        Los datos mostrados son sintéticos. Desactívalo en
        <router-link to="/settings" class="arb-demo-banner__link">Configuración</router-link>.
      </span>
    </div>
    <main class="arb-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.arb-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.arb-menubar {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  background: var(--arb-bg-surface);
  border-bottom: 1px solid var(--arb-border);
}

.arb-brand {
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--arb-accent-primary);
  padding-right: 1.5rem;
}

.arb-nav-label {
  margin-left: 0.4rem;
}

.arb-nav-active {
  color: var(--arb-accent-primary) !important;
}

.arb-main {
  flex: 1;
  padding: 1.5rem;
  background: var(--arb-bg-base);
}

.arb-menubar-end {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Banner Modo Demo — banda naranja bajo el menubar */
.arb-demo-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 1.5rem;
  background: rgba(255, 165, 2, 0.12);
  border-bottom: 1px solid rgba(255, 165, 2, 0.4);
  font-size: 0.82rem;
  color: var(--arb-warning);
}

.arb-demo-banner__icon {
  font-size: 0.9rem;
  flex-shrink: 0;
}

.arb-demo-banner__link {
  color: var(--arb-warning);
  text-decoration: underline;
  font-weight: 600;
}

.arb-demo-banner__link:hover {
  color: var(--arb-text-primary);
}
</style>
