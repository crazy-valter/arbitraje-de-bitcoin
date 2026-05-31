<script setup lang="ts">
// 1. Imports
import { ref, computed, watch } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useConfigStore } from '@/stores/config.store'

// 2. Props y emits — ninguno (card autónoma)

// 3. Stores
const configStore = useConfigStore()

// 4. State local
const confirm = useConfirm()
const isToggling = ref(false)
const localMockMode = ref(configStore.config.mockModeEnabled)

// 5. Computed
const isMockActive = computed(() => configStore.config.mockModeEnabled)

// 6. Watchers
// Sincronizar localMockMode cuando el store cambie (ej: al montar la vista)
watch(() => configStore.config.mockModeEnabled, (val) => {
  localMockMode.value = val
})

// 7. Lifecycle hooks — ninguno

// 8. Funciones/handlers
function onToggleRequest(newValue: boolean): void {
  // Revertir el toggle visualmente hasta que el usuario confirme
  localMockMode.value = !newValue

  confirm.require({
    group: 'mock-mode',
    header: newValue ? 'Activar Modo Demo' : 'Desactivar Modo Demo',
    message: newValue
      ? 'Se desconectarán los feeds de mercado reales (Binance, Bybit, Kraken) y se activará el generador de precios sintéticos. Los datos mostrados en el Dashboard serán ficticios hasta que desactives el Modo Demo. ¿Continuar?'
      : 'Se reconectará el sistema a los feeds reales de Binance, Bybit y Kraken. El Dashboard mostrará datos de mercado en tiempo real. ¿Continuar?',
    icon: newValue ? 'pi pi-exclamation-triangle' : 'pi pi-info-circle',
    acceptLabel: newValue ? 'Activar' : 'Desactivar',
    rejectLabel: 'Cancelar',
    accept: () => applyToggle(newValue),
    reject: () => { /* localMockMode ya fue revertido arriba */ },
  })
}

async function applyToggle(newValue: boolean): Promise<void> {
  isToggling.value = true
  await configStore.toggleMockMode(newValue)
  isToggling.value = false
}
</script>

<template>
  <section class="settings-section" :class="{ 'mock-mode-active': isMockActive }">
    <div class="mock-mode-header">
      <h2 class="settings-section-title">Modo Demo — Simulación de Mercado</h2>
      <ToggleButton
        v-model="localMockMode"
        :on-label="'Desactivar Modo Demo'"
        :off-label="'Activar Modo Demo'"
        :on-icon="'pi pi-stop-circle'"
        :off-icon="'pi pi-play'"
        :disabled="isToggling"
        @update:model-value="onToggleRequest"
      />
    </div>

    <!-- Banner de advertencia — solo cuando activo -->
    <Message v-if="isMockActive" severity="warn" :closable="false" class="mock-warning-banner">
      Modo Demo activo — el sistema no está conectado a exchanges reales. Los datos mostrados son sintéticos para propósitos de validación.
    </Message>

    <!-- Descripción siempre visible -->
    <div class="mock-description">
      <p>
        En condiciones normales de mercado, las divergencias de precio entre Binance, Bybit y Kraken
        son inferiores al 0.1%. Después de descontar comisiones de trading (0.10%–0.26%) y slippage,
        la mayoría de estas diferencias no superan el umbral mínimo de rentabilidad y son correctamente
        descartadas por el motor — esto es el comportamiento esperado y correcto del sistema.
      </p>
      <p>
        El Modo Demo activa un generador de precios sintéticos con spreads artificialmente grandes
        ($300–$600 entre exchanges). Esto permite verificar visualmente que toda la cadena funciona:
        detección → cálculo de fees → simulación de trades → actualización de wallets → persistencia
        → SSE → Dashboard en tiempo real.
      </p>
      <p>
        Los datos generados en Modo Demo son ficticios y no representan condiciones reales de mercado.
      </p>
    </div>

    <!-- ConfirmDialog con grupo exclusivo para esta card -->
    <ConfirmDialog group="mock-mode" />
  </section>
</template>

<style scoped>
.settings-section {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: border-color 0.2s;
}

.mock-mode-active {
  border-color: var(--arb-warning);
}

.mock-mode-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
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

.mock-description p {
  font-size: 0.85rem;
  color: var(--arb-text-secondary);
  margin: 0 0 0.5rem;
  line-height: 1.5;
}

.mock-description p:last-child {
  margin-bottom: 0;
}

.mock-warning-banner {
  /* sin override adicional — PrimeVue Message severity="warn" aplica el color correcto */
}
</style>
