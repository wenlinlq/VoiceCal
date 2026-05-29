<template>
  <!-- #ifdef H5 -->
  <Teleport to="body">
    <div v-if="mounted" class="confirm-overlay" :class="{ active }">
      <div class="confirm-mask" @click="onCancel" />
      <div class="confirm-dialog" @click.stop>
        <span class="confirm-title">{{ title }}</span>
        <span class="confirm-message">{{ message }}</span>

        <div v-if="event" class="event-preview">
          <span class="preview-title">{{ event.title }}</span>
          <span class="preview-time">{{ timeRange }}</span>
        </div>

        <div class="confirm-actions">
          <button type="button" class="btn btn-cancel" @click="onCancel">
            {{ cancelText }}
          </button>
          <button
            type="button"
            class="btn btn-confirm"
            :class="{ danger: variant === 'danger' }"
            @click="onConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
  <!-- #endif -->

  <!-- #ifndef H5 -->
  <view v-if="mounted" class="confirm-overlay" :class="{ active }">
    <view class="confirm-mask" @tap="onCancel" />
    <view class="confirm-dialog" @tap.stop>
      <text class="confirm-title">{{ title }}</text>
      <text class="confirm-message">{{ message }}</text>

      <view v-if="event" class="event-preview">
        <text class="preview-title">{{ event.title }}</text>
        <text class="preview-time">{{ timeRange }}</text>
      </view>

      <view class="confirm-actions">
        <view class="btn btn-cancel" @tap="onCancel">
          <text>{{ cancelText }}</text>
        </view>
        <view
          class="btn btn-confirm"
          :class="{ danger: variant === 'danger' }"
          @tap="onConfirm"
        >
          <text>{{ confirmText }}</text>
        </view>
      </view>
    </view>
  </view>
  <!-- #endif -->
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from "vue";
import { rafTwice } from "@/utils/raf.js";
import { formatTime } from "@/utils/date.js";

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: "请确认" },
  message: { type: String, default: "" },
  event: { type: Object, default: null },
  variant: { type: String, default: "default" },
  confirmText: { type: String, default: "确认" },
  cancelText: { type: String, default: "取消" },
});

const emit = defineEmits(["confirm", "cancel"]);

const ANIM_DURATION = 280;

const mounted = ref(false);
const active = ref(false);
let hideTimer = null;

const timeRange = computed(() => {
  if (!props.event) return "";
  const start = formatTime(props.event.start_time);
  const end = props.event.end_time ? formatTime(props.event.end_time) : "";
  return end ? `${start} - ${end}` : start;
});

watch(
  () => props.visible,
  (val) => {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    if (val) {
      mounted.value = true;
      rafTwice(() => {
        active.value = true;
      });
    } else if (mounted.value) {
      active.value = false;
      hideTimer = setTimeout(() => {
        mounted.value = false;
      }, ANIM_DURATION);
    }
  },
);

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer);
});

function onConfirm() {
  emit("confirm");
}

function onCancel() {
  emit("cancel");
}
</script>

<style lang="scss" scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
}

.confirm-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0);
  transition: background-color 0.28s ease;
}

.confirm-overlay.active .confirm-mask {
  background: rgba(0, 0, 0, 0.5);
}

.confirm-dialog {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 40rpx;
  box-sizing: border-box;
  opacity: 0;
  transform: scale(0.92);
  transition:
    opacity 0.28s ease,
    transform 0.28s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.confirm-overlay.active .confirm-dialog {
  opacity: 1;
  transform: scale(1);
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
  background: #f5f9ff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 32rpx;
  border-left: 6rpx solid #1a73e8;
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
  color: #1a73e8;
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
  border: none;
  font-family: inherit;
  cursor: pointer;

  &:active {
    opacity: 0.85;
  }
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.btn-confirm {
  background: #1a73e8;
  color: #fff;

  &.danger {
    background: #ff6b6b;
  }
}

/* #ifdef H5 */
.confirm-overlay {
  padding: 24px;
}

.confirm-dialog {
  max-width: 360px;
  border-radius: 20px;
  padding: 24px 20px 20px;
}

.confirm-title {
  font-size: 18px;
  margin-bottom: 8px;
}

.confirm-message {
  font-size: 14px;
  margin-bottom: 16px;
}

.event-preview {
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 20px;
}

.preview-title {
  font-size: 16px;
}

.preview-time {
  font-size: 14px;
}

.confirm-actions {
  gap: 12px;
}

.btn {
  height: 44px;
  border-radius: 22px;
  font-size: 15px;
}
/* #endif */
</style>
