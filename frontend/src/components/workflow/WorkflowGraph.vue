<template>
  <div>
    <div class="workflow-graph">
      <VueFlow
        ref="flowRef"
        :nodes="nodes"
        :edges="edges"
        :min-zoom="0.25"
        :max-zoom="1.75"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :zoom-on-scroll="true"
        :pan-on-scroll="true"
        :fit-view-on-init="true"
      >
        <template #node-stage="nodeProps">
          <StageNode v-bind="nodeProps" />
        </template>
        <template #edge-loop="edgeProps">
          <LoopEdge v-bind="edgeProps" />
        </template>
        <Background :gap="18" pattern-color="#d5e6e5" />
        <Controls position="bottom-right" />
      </VueFlow>
    </div>

    <!-- 驳回回路说明（红色虚线回边 + 原因） -->
    <div v-if="loops.length > 0" class="loop-legend">
      <div class="loop-legend-title">
        <el-icon><WarningFilled /></el-icon>
        驳回回路（秘书复核 → 部门处理）
      </div>
      <div v-for="(loop, i) in loops" :key="i" class="loop-legend-item">
        {{ loop.department || `任务 #${loop.task_id}` }} · {{ formatDateTime(loop.at) }}
        <span v-if="loop.comment">：{{ loop.comment }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { VueFlow, MarkerType, Position, type Edge, type Node } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

import StageNode from './StageNode.vue'
import LoopEdge from './LoopEdge.vue'
import type { Workflow, WorkflowLoop } from '@/types'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{ workflow: Workflow | null | undefined }>()

const NODE_GAP = 230

type StageState = 'current' | 'reached' | 'pending'

const nodes = computed<Node[]>(() => {
  const stages = props.workflow?.stages ?? []
  const current = props.workflow?.current ?? ''
  return stages.map((s, i): Node => {
    const state: StageState = s.key === current ? 'current' : s.reached ? 'reached' : 'pending'
    return {
      id: s.key,
      type: 'stage',
      position: { x: i * NODE_GAP, y: 40 },
      data: { label: s.label, time: s.at ? formatDateTime(s.at) : '', state },
      draggable: false,
      connectable: false,
      selectable: false,
      deletable: false,
    }
  })
})

const edges = computed<Edge[]>(() => {
  const stages = props.workflow?.stages ?? []
  const out: Edge[] = []
  for (let i = 0; i < stages.length - 1; i++) {
    const nextReached = stages[i + 1].reached
    const color = nextReached ? '#0e7a78' : '#c8c9cc'
    out.push({
      id: `e-${stages[i].key}-${stages[i + 1].key}`,
      source: stages[i].key,
      target: stages[i + 1].key,
      type: 'smoothstep',
      animated: false,
      style: { stroke: color, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color },
    })
  }
  ;(props.workflow?.loops ?? []).forEach((loop, idx) => {
    out.push({
      id: `loop-${loop.task_id}-${idx}`,
      source: 'SECRETARY_TASK_REVIEW',
      target: 'DEPARTMENT_PROCESSING',
      type: 'loop',
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: { department: loop.department, at: loop.at, comment: loop.comment },
      animated: false,
    } as Edge)
  })
  return out
})

const loops = computed<WorkflowLoop[]>(() => props.workflow?.loops ?? [])

// 数据异步到达后重新适配视口
const flowRef = ref<InstanceType<typeof VueFlow> | null>(null)
watch(
  () => props.workflow,
  () => {
    if (props.workflow) {
      nextTick(() => {
        void flowRef.value?.fitView({ padding: 0.25 })
      })
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.workflow-graph :deep(.vue-flow__node) {
  font-family: inherit;
}
</style>
