<template>
  <g class="loop-edge-group">
    <title>{{ tooltip }}</title>
    <BaseEdge :id="id" :path="pathData.path" :style="loopStyle" />
    <text :x="pathData.labelX" :y="pathData.labelY" class="loop-edge-label" text-anchor="middle">
      驳回
    </text>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'
import { BaseEdge, getSmoothStepPath, Position, type EdgeProps } from '@vue-flow/core'

import { formatDateTime } from '@/utils/format'

const props = defineProps<EdgeProps>()

const pathData = computed(() => {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition ?? Position.Bottom,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition ?? Position.Top,
    borderRadius: 20,
    offset: 120,
  })
  return { path, labelX, labelY }
})

const loopStyle: CSSProperties = {
  stroke: '#f56c6c',
  strokeWidth: 2,
  strokeDasharray: '6 6',
}

/** 悬停提示：部门 + 时间 + 驳回原因 */
const tooltip = computed(() => {
  const data = props.data as { department?: string; at?: string; comment?: string } | undefined
  const parts: string[] = []
  if (data?.department) parts.push(data.department)
  if (data?.at) parts.push(formatDateTime(data.at))
  if (data?.comment) parts.push(`原因：${data.comment}`)
  return parts.join(' · ') || '驳回'
})
</script>

<style scoped>
.loop-edge-label {
  font-size: 12px;
  fill: #f56c6c;
  font-weight: 600;
  paint-order: stroke;
  stroke: #fff;
  stroke-width: 4px;
  pointer-events: none;
}
</style>
