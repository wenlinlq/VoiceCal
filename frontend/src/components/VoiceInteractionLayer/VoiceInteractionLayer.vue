<template>
  <view v-if="mounted" class="voice-layer" :class="{ active: active }">
    <view class="voice-mask" />

    <view class="voice-panel-wrap">
      <VoiceStatus
        :agent-state="agentState"
        :asr-text="asrText"
        :visible="true"
        centered
      />
    </view>

    <view class="voice-mic-wrap">
      <RecordButton
        :status="status"
        :disabled="disabled"
        position="bottom"
        @start="$emit('start')"
        @stop="$emit('stop')"
      />
    </view>
  </view>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { rafTwice } from '@/utils/raf.js'
import VoiceStatus from '@/components/VoiceStatus/VoiceStatus.vue'
import RecordButton from '@/components/RecordButton/RecordButton.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  status: { type: String, default: 'idle' },
  agentState: { type: String, default: 'listening' },
  asrText: { type: String, default: '' },
  disabled: { type: Boolean, default: false }
})

defineEmits(['start', 'stop'])

const mounted = ref(false)
const active = ref(false)
let hideTimer = null

watch(
  () => props.show,
  (val) => {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
    if (val) {
      mounted.value = true
      rafTwice(() => {
        active.value = true
      })
    } else {
      active.value = false
      hideTimer = setTimeout(() => {
        mounted.value = false
      }, 380)
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<style lang="scss" scoped>
.voice-layer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 500;
  pointer-events: none;

  &.active {
    pointer-events: auto;
  }
}

.voice-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.35s ease;
}

.voice-layer.active .voice-mask {
  background-color: rgba(0, 0, 0, 0.42);
}

.voice-panel-wrap {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.96);
  z-index: 2;
  opacity: 0;
  transition: opacity 0.35s ease, transform 0.35s ease;
  pointer-events: none;
  width: 100%;
  display: flex;
  justify-content: center;
  padding: 0 48rpx;
  box-sizing: border-box;
}

.voice-layer.active .voice-panel-wrap {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
}

.voice-mic-wrap {
  position: absolute;
  left: 50%;
  bottom: calc(40rpx + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 3;
  pointer-events: auto;
}
</style>
