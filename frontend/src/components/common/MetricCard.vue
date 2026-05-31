<script setup lang="ts">
// Props de la tarjeta KPI
defineProps<{
  label: string
  value: string
  subvalue?: string
  trend?: 'up' | 'down' | 'neutral'
}>()
</script>

<template>
  <Card class="arb-metric-card">
    <template #content>
      <div class="metric-label">{{ label }}</div>
      <div class="metric-value arb-mono">{{ value }}</div>
      <div
        v-if="subvalue"
        class="metric-sub"
        :class="`metric-sub--${trend ?? 'neutral'}`"
      >
        <i
          v-if="trend === 'up'"
          class="pi pi-arrow-up metric-icon"
        />
        <i
          v-else-if="trend === 'down'"
          class="pi pi-arrow-down metric-icon"
        />
        {{ subvalue }}
      </div>
    </template>
  </Card>
</template>

<style scoped>
.arb-metric-card {
  background: var(--arb-bg-surface);
  border: 1px solid var(--arb-border);
  height: 100%;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--arb-text-secondary);
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--arb-text-primary);
}

.metric-sub {
  font-size: 0.75rem;
  margin-top: 0.35rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.metric-sub--up      { color: var(--arb-profit); }
.metric-sub--down    { color: var(--arb-loss); }
.metric-sub--neutral { color: var(--arb-text-muted); }

.metric-icon {
  font-size: 0.65rem;
}
</style>
