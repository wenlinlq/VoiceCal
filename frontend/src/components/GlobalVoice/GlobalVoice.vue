<template>
  <!-- 全局底部居中麦克风 -->
  <view v-if="!showVoiceLayer" class="global-mic">
    <RecordButton
      :status="voiceStore.status"
      position="bottom"
      @start="onRecordStart"
      @stop="onRecordStop"
    />
  </view>

  <!-- 语音交互遮罩层 -->
  <VoiceInteractionLayer
    :show="showVoiceLayer"
    :status="voiceStore.status"
    :agent-state="agentState"
    :asr-text="voiceStore.displayText"
    :disabled="voiceStore.status === 'processing'"
    @start="onRecordStart"
    @stop="onRecordStop"
  />
</template>

<script setup>
import { useVoiceInteraction } from '@/composables/useVoiceInteraction.js'
import RecordButton from '@/components/RecordButton/RecordButton.vue'
import VoiceInteractionLayer from '@/components/VoiceInteractionLayer/VoiceInteractionLayer.vue'

const {
  voiceStore,
  agentState,
  showVoiceLayer,
  onRecordStart,
  onRecordStop
} = useVoiceInteraction()
</script>

<style lang="scss" scoped>
.global-mic {
  position: fixed;
  left: 50%;
  bottom: calc(40rpx + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 400;
  pointer-events: auto;
}
</style>
