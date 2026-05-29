<template>
  <view
    class="record-btn"
    :class="[`status-${status}`, `pos-${position}`, { disabled }]"
    @touchstart.prevent="onTouchStart"
    @touchend.prevent="onTouchEnd"
    @touchcancel.prevent="onTouchEnd"
    @mousedown.prevent="onTouchStart"
    @mouseup.prevent="onTouchEnd"
    @mouseleave.prevent="onTouchEnd"
  >
    <view v-if="status === 'recording'" class="wave-ring ring-1" />
    <view v-if="status === 'recording'" class="wave-ring ring-2" />
    <view v-if="status === 'recording'" class="wave-ring ring-3" />

    <view class="btn-inner">
      <text v-if="status === 'idle'" class="btn-icon">🎤</text>
      <text v-else-if="status === 'recording'" class="btn-icon">⏹️</text>
      <view v-else-if="status === 'processing'" class="loading-spinner" />
      <text v-else class="btn-icon">🎤</text>
      <text class="btn-text">{{ statusText }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'idle',
    validator: (v) => ['idle', 'recording', 'processing', 'speaking'].includes(v)
  },
  disabled: { type: Boolean, default: false },
  position: { type: String, default: 'bottom' }
})

const emit = defineEmits(['start', 'stop'])

const statusText = computed(() => {
  const map = {
    idle: '长按说话',
    recording: '松手结束',
    processing: '处理中',
    speaking: '播报中'
  }
  return map[props.status] || '长按说话'
})

function onTouchStart() {
  if (props.disabled || props.status === 'processing') return
  if (props.status === 'idle') {
    emit('start')
  }
}

function onTouchEnd() {
  if (props.disabled || props.status !== 'recording') return
  emit('stop')
}
</script>

<style lang="scss" scoped>
@import './RecordButton.scss';
</style>
