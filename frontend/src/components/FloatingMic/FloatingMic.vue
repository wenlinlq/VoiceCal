<template>
  <view v-if="show" class="floating-mic" :style="safeStyle">
    <RecordButton
      :status="status"
      :disabled="disabled"
      position="bottom"
      @start="$emit('start')"
      @stop="$emit('stop')"
    />
  </view>
</template>

<script setup>
import RecordButton from '@/components/RecordButton/RecordButton.vue'

defineProps({
  show: { type: Boolean, default: true },
  status: { type: String, default: 'idle' },
  disabled: { type: Boolean, default: false },
  safeStyle: { type: Object, default: () => ({}) }
})

defineEmits(['start', 'stop'])
</script>

<style lang="scss" scoped>
.floating-mic {
  position: fixed;
  right: 48rpx;
  bottom: calc(48rpx + env(safe-area-inset-bottom));
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
