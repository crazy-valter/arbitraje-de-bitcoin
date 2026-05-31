<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const requestedPath = computed(() => route.path)

const targetRoute = computed(() =>
  auth.isAuthenticated ? { name: 'dashboard' } : { name: 'login' },
)
const targetLabel = computed(() =>
  auth.isAuthenticated ? 'Volver al Dashboard' : 'Ir al Login',
)

function goBack(): void {
  void router.push(targetRoute.value)
}
</script>

<template>
  <div class="nf-page">
    <!-- Blobs decorativos de fondo -->
    <div class="nf-blob nf-blob--tl" />
    <div class="nf-blob nf-blob--br" />

    <div class="nf-card">
      <!-- Logo -->
      <div class="nf-logo">
        <span class="nf-logo__icon">
          <i class="pi pi-bitcoin" />
        </span>
        <span class="nf-logo__text">ArbitrageBot</span>
      </div>

      <!-- Código de error -->
      <p class="nf-code arb-mono">404</p>

      <!-- Icono de señal -->
      <span class="nf-icon-wrap">
        <i class="pi pi-map-marker nf-icon" />
      </span>

      <!-- Heading -->
      <h1 class="nf-heading">Ruta no encontrada</h1>
      <p class="nf-subheading">
        La ruta
        <code class="nf-path arb-mono">{{ requestedPath }}</code>
        no existe en este sistema.
      </p>

      <!-- Acción principal -->
      <Button
        :label="targetLabel"
        icon="pi pi-arrow-left"
        class="nf-btn"
        @click="goBack"
      />
    </div>
  </div>
</template>

<style scoped>
/* ──────────────────────────────────── Page ───────────────────────────────── */
.nf-page {
  position: relative;
  min-height: 100vh;
  min-width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--arb-bg-base);
  overflow: hidden;
  padding: 1.5rem;
}

/* Blobs decorativos */
.nf-blob {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.nf-blob--tl {
  top: -80px;
  left: -80px;
  width: 300px;
  height: 300px;
  background: rgba(0, 212, 170, 0.07);
}

.nf-blob--br {
  bottom: -60px;
  right: -60px;
  width: 240px;
  height: 240px;
  background: rgba(0, 212, 170, 0.05);
}

/* ──────────────────────────────────── Card ───────────────────────────────── */
.nf-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 24px;
  padding: 2.5rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* ──────────────────────────────────── Logo ───────────────────────────────── */
.nf-logo {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 2rem;
}

.nf-logo__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  background: var(--arb-accent-primary);
  color: #fff;
  font-size: 1rem;
}

.nf-logo__text {
  font-size: 1rem;
  font-weight: 700;
  color: var(--arb-text-primary);
}

/* ───────────────────────────────── Código 404 ────────────────────────────── */
.nf-code {
  font-size: 5rem;
  font-weight: 700;
  line-height: 1;
  color: var(--arb-accent-primary);
  margin: 0 0 1.25rem;
  letter-spacing: -0.04em;
}

/* ────────────────────────────────── Icono ────────────────────────────────── */
.nf-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  border: 1px solid var(--arb-border);
  background: var(--arb-bg-elevated);
  margin-bottom: 1.25rem;
}

.nf-icon {
  font-size: 1.25rem;
  color: var(--arb-text-muted);
}

/* ─────────────────────────────── Textos ─────────────────────────────────── */
.nf-heading {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--arb-text-primary);
  margin: 0 0 0.625rem;
}

.nf-subheading {
  font-size: 0.875rem;
  color: var(--arb-text-secondary);
  margin: 0 0 2rem;
  line-height: 1.6;
}

.nf-path {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  background: var(--arb-bg-elevated);
  color: var(--arb-text-primary);
  font-size: 0.8125rem;
  border: 1px solid var(--arb-border);
}

/* ─────────────────────────────── Botón ──────────────────────────────────── */
.nf-btn {
  width: 100%;
  --p-button-primary-background: var(--arb-accent-primary);
  --p-button-primary-hover-background: var(--arb-accent-hover);
  --p-button-primary-active-background: var(--arb-accent-hover);
  --p-button-primary-border-color: var(--arb-accent-primary);
  --p-button-primary-hover-border-color: var(--arb-accent-hover);
  --p-button-primary-active-border-color: var(--arb-accent-hover);
}

/* ──────────────────────────────── Responsive ─────────────────────────────── */
@media (max-width: 480px) {
  .nf-card {
    padding: 2rem 1.25rem;
    border-radius: 20px;
  }

  .nf-code {
    font-size: 4rem;
  }
}
</style>
