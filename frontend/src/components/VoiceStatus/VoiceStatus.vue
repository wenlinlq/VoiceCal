<template>
  <view v-if="show" class="voice-status" :class="{ centered }">
    <view class="status-icon-wrap">
      <view v-if="isListening" class="mini-wave">
        <view class="bar" />
        <view class="bar" />
        <view class="bar" />
      </view>
      <view v-if="status === 'thinking'" class="thinking-spinner" />
      <view v-if="status === 'speaking'" class="speaking-bars">
        <view class="bar" />
        <view class="bar" />
        <view class="bar" />
      </view>
    </view>
    <view class="status-text-wrap">
      <text class="status-label">{{ label }}</text>
      <text v-if="mainText" class="reply-text">{{ mainText }}</text>
      <text v-if="hintText" class="hint-text">{{ hintText }}</text>
      <text v-if="userText && showUserText" class="user-text">{{
        userText
      }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  status: {
    type: String,
    default: "idle",
    validator: (v) =>
      ["idle", "recording", "thinking", "speaking", "auto_listening"].includes(
        v,
      ),
  },
  replyText: { type: String, default: "" },
  errorText: { type: String, default: "" },
  userText: { type: String, default: "" },
  needConfirm: { type: Boolean, default: false },
  queryListenMode: { type: Boolean, default: false },
  visible: { type: Boolean, default: true },
  centered: { type: Boolean, default: false },
});

const show = computed(() => props.visible);

const isListening = computed(
  () => props.status === "recording" || props.status === "auto_listening",
);

const label = computed(() => {
  if (props.errorText) return "提示";
  const map = {
    recording: "聆听中...",
    thinking: "思考中...",
    speaking: "播报中",
    auto_listening: "聆听中...",
  };
  return map[props.status] || "";
});

const mainText = computed(() => {
  if (props.errorText) return props.errorText;
  if (!props.replyText) return "";
  if (props.status === "speaking") return props.replyText;
  if ((props.needConfirm || props.queryListenMode) && isListening.value) {
    return props.replyText;
  }
  return "";
});

const hintText = computed(() => {
  if (props.queryListenMode && isListening.value) {
    return "点击空白位置可结束对话，5 秒无声音将自动结束";
  }
  if (props.needConfirm && isListening.value) {
    return "请说「确认」或「取消」，也可点弹窗按钮";
  }
  if (props.status === "auto_listening") {
    return "请说话…（3 秒无声音 Agent 会再说一遍）";
  }
  if (props.status === "recording") {
    return "请说话...";
  }
  if (props.status === "speaking") {
    return "Agent 播报中，请稍候";
  }
  return "";
});

const showUserText = computed(() => {
  return Boolean(props.userText) && props.status === "speaking";
});
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
  box-shadow: 0 4rpx 16rpx rgba(26, 115, 232, 0.08);
  border-left: 6rpx solid #1a73e8;

  &.centered {
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin: 0;
    width: 100%;
    max-width: 100%;
    padding: 48rpx 40rpx;
    border-left: none;
    border-radius: 24rpx;
    box-shadow: 0 12rpx 48rpx rgba(0, 0, 0, 0.12);
    box-sizing: border-box;
  }
}

.status-icon-wrap {
  position: relative;
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  .centered & {
    width: 80rpx;
    height: 80rpx;
    margin-bottom: 8rpx;
  }
}

.mini-wave,
.speaking-bars {
  display: flex;
  gap: 6rpx;
  align-items: flex-end;
  height: 32rpx;

  .bar {
    width: 6rpx;
    background: #1a73e8;
    border-radius: 3rpx;
    animation: bar-bounce 0.6s ease-in-out infinite;

    &:nth-child(1) {
      animation-delay: 0s;
      height: 12rpx;
    }
    &:nth-child(2) {
      animation-delay: 0.15s;
      height: 24rpx;
    }
    &:nth-child(3) {
      animation-delay: 0.3s;
      height: 16rpx;
    }
  }
}

.speaking-bars .bar {
  animation: bar-bounce 0.5s ease-in-out infinite alternate;
}

@keyframes bar-bounce {
  0%,
  100% {
    transform: scaleY(0.6);
  }
  50% {
    transform: scaleY(1.2);
  }
}

.thinking-spinner {
  width: 48rpx;
  height: 48rpx;
  border: 3rpx solid #f0f0f0;
  border-top-color: #1a73e8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;

  .centered & {
    width: 56rpx;
    height: 56rpx;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.status-text-wrap {
  flex: 1;
  min-width: 0;

  .centered & {
    flex: none;
    width: 100%;
  }
}

.status-label {
  font-size: 28rpx;
  color: #1a73e8;
  font-weight: 500;
  display: block;

  .centered & {
    font-size: 30rpx;
  }
}

.reply-text {
  font-size: 26rpx;
  color: #333;
  display: block;
  margin-top: 8rpx;
  line-height: 1.5;
  word-break: break-all;

  .centered & {
    font-size: 32rpx;
    margin-top: 16rpx;
    color: #1a1a1a;
    font-weight: 500;
  }
}

.hint-text {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-top: 12rpx;
  line-height: 1.4;

  .centered & {
    font-size: 26rpx;
  }
}

.user-text {
  font-size: 24rpx;
  color: #888;
  display: block;
  margin-top: 12rpx;
  line-height: 1.4;
  word-break: break-all;

  .centered & {
    font-size: 26rpx;
  }
}
</style>
