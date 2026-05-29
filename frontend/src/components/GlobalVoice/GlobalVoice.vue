<template>
  <!-- 底部麦克风：始终显示，会话中可再次点击终止 -->
  <view
    class="global-mic"
    :class="{ 'in-session': inSession }"
    :style="micWrapStyle"
  >
    <RecordButton
      :status="voiceStore.status"
      :in-session="inSession"
      position="bottom"
      @tap="onMicClick"
    />
  </view>

  <!-- 会话中：遮罩 + 状态面板 -->
  <VoiceInteractionLayer
    :show="showVoiceLayer"
    :status="voiceStore.status"
    :reply-text="voiceStore.replyText"
    :error-text="voiceStore.errorText"
    :user-text="voiceStore.userText"
    @close="closeVoiceSession"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useVoiceInteraction } from '@/composables/useVoiceInteraction.js'
import { useMpSafeArea } from '@/composables/useMpSafeArea.js'
import { VOICE_STATUS } from '@/store/modules/voice.js'
import RecordButton from '@/components/RecordButton/RecordButton.vue'
import VoiceInteractionLayer from '@/components/VoiceInteractionLayer/VoiceInteractionLayer.vue'

const {
  voiceStore,
  showVoiceLayer,
  onMicClick,
  closeVoiceSession,
} = useVoiceInteraction()

const { micWrapStyle } = useMpSafeArea()

const inSession = computed(() => voiceStore.status !== VOICE_STATUS.IDLE)
</script>

<style lang="scss" scoped>
.global-mic {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  z-index: 400;
  pointer-events: auto;

  /* #ifndef MP-WEIXIN */
  bottom: calc(40rpx + env(safe-area-inset-bottom));
  /* #endif */

  &.in-session {
    z-index: 510;
  }
}
</style>
