<template>
  <div class="stage-node" :class="stateClass">
    <Handle type="target" :position="Position.Left" />
    <div class="stage-label">{{ data.label }}</div>
    <div v-if="data.time" class="stage-time">{{ data.time }}</div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position, type NodeProps } from '@vue-flow/core'

const props = defineProps<NodeProps>()

const state = computed(() => (props.data?.state as string) || 'pending')

const stateClass = computed(() => {
  if (state.value === 'current') return 'is-current'
  if (state.value === 'reached') return 'is-reached'
  return 'is-pending'
})
</script>

<style scoped>
.stage-node {
  min-width: 150px;
  max-width: 190px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  text-align: center;
  transition: all 0.25s;
  line-height: 1.5;
}

.stage-node.is-reached {
  background: #e6f4f3;
  border: 1px solid #8ec6c4;
  color: #0b615f;
}

.stage-node.is-pending {
  background: #f7f8fa;
  border: 1px dashed #d3d6dc;
  color: #9aa0a6;
}

.stage-node.is-current {
  background: #0e7a78;
  border: 2px solid #0b615f;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 0 0 4px rgba(14, 122, 120, 0.22);
}

.stage-label {
  word-break: break-all;
}

.stage-time {
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.75;
}
</style>
