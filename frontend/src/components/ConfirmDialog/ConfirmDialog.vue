<template>
  <view v-if="visible" class="confirm-mask" @tap="onCancel">
    <view class="confirm-dialog" @tap.stop>
      <text class="confirm-title">请确认</text>
      <text class="confirm-message">{{ message }}</text>

      <view v-if="event" class="event-preview">
        <text class="preview-title">{{ event.title }}</text>
        <text class="preview-time">🕐 {{ timeRange }}</text>
      </view>

      <view class="confirm-actions">
        <view class="btn btn-cancel" @tap="onCancel">
          <text>取消</text>
        </view>
        <view class="btn btn-confirm" @tap="onConfirm">
          <text>确认</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { formatTime } from '@/utils/date.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: '' },
  event: { type: Object, default: null }
})

const emit = defineEmits(['confirm', 'cancel'])

const timeRange = computed(() => {
  if (!props.event) return ''
  const start = formatTime(props.event.start_time)
  const end = props.event.end_time ? formatTime(props.event.end_time) : ''
  return end ? `${start} - ${end}` : start
})

function onConfirm() {
  emit('confirm')
}

function onCancel() {
  emit('cancel')
}
</script>

<style lang="scss" scoped>
.confirm-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 48rpx;
}

.confirm-dialog {
  width: 100%;
  max-width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 40rpx;
  animation: pop-in 0.25s ease;
}

@keyframes pop-in {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.confirm-title {
  font-size: 34rpx;
  font-weight: 600;
  color: #333;
  display: block;
  text-align: center;
  margin-bottom: 16rpx;
}

.confirm-message {
  font-size: 28rpx;
  color: #666;
  display: block;
  text-align: center;
  line-height: 1.5;
  margin-bottom: 24rpx;
}

.event-preview {
  background: #f8f9ff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 32rpx;
  border-left: 6rpx solid #667eea;
}

.preview-title {
  font-size: 30rpx;
  font-weight: 500;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.preview-time {
  font-size: 26rpx;
  color: #667eea;
  display: block;
}

.confirm-actions {
  display: flex;
  gap: 24rpx;
}

.btn {
  flex: 1;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 40rpx;
  font-size: 28rpx;
  font-weight: 500;

  &:active {
    opacity: 0.85;
  }
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.btn-confirm {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}
</style>
