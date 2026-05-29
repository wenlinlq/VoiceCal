<template>
  <view v-if="show" class="voice-status" :class="`state-${agentState}`">
    <view class="status-icon-wrap">
      <text class="status-icon">{{ icon }}</text>
      <view v-if="agentState === 'listening'" class="mini-wave">
        <view class="bar" />
        <view class="bar" />
        <view class="bar" />
      </view>
      <view v-if="agentState === 'thinking'" class="thinking-spinner" />
    </view>
    <view class="status-text-wrap">
      <text class="status-label">{{ label }}</text>
      <text v-if="asrText" class="asr-text">{{ asrText }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agentState: {
    type: String,
    default: 'listening',
    validator: (v) => ['listening', 'thinking', 'speaking', 'waiting_confirm'].includes(v)
  },
  asrText: { type: String, default: '' },
  visible: { type: Boolean, default: true }
})

const show = computed(() => props.visible && props.agentState !== 'idle')

const icon = computed(() => {
  const map = {
    listening: '🎤',
    thinking: '🤔',
    speaking: '🔊',
    waiting_confirm: '✋'
  }
  return map[props.agentState] || '🎤'
})

const label = computed(() => {
  const map = {
    listening: '识别中...',
    thinking: '思考中...',
    speaking: '播报中...',
    waiting_confirm: '请确认'
  }
  return map[props.agentState] || ''
})
</script>

<style lang="scss" scoped>
.voice-status {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin: 0 24rpx 16rpx;
  padding: 20rpx 24rpx;
  background: #fff;
  border-radius: 16rpx;
  box-shadow: 0 4rpx 16rpx rgba(102, 126, 234, 0.1);
  border-left: 6rpx solid #667eea;
  animation: slide-down 0.3s ease;
}

@keyframes slide-down {
  from {
    transform: translateY(-20rpx);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.status-icon-wrap {
  position: relative;
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-icon {
  font-size: 36rpx;
}

.mini-wave {
  position: absolute;
  bottom: 0;
  display: flex;
  gap: 4rpx;
  align-items: flex-end;
  height: 20rpx;

  .bar {
    width: 4rpx;
    background: #667eea;
    border-radius: 2rpx;
    animation: bar-bounce 0.6s ease-in-out infinite;

    &:nth-child(1) { animation-delay: 0s; height: 8rpx; }
    &:nth-child(2) { animation-delay: 0.15s; height: 16rpx; }
    &:nth-child(3) { animation-delay: 0.3s; height: 10rpx; }
  }
}

@keyframes bar-bounce {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1.2); }
}

.thinking-spinner {
  position: absolute;
  width: 48rpx;
  height: 48rpx;
  border: 3rpx solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-text-wrap {
  flex: 1;
  min-width: 0;
}

.status-label {
  font-size: 28rpx;
  color: #667eea;
  font-weight: 500;
  display: block;
}

.asr-text {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-top: 4rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
