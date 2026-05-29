<template>
  <view class="swipe-item" :class="{ 'is-completed': event.completed }">
    <view
      class="swipe-track"
      :class="{ dragging: isDragging }"
      :style="trackStyle"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      @touchcancel="onTouchEnd"
    >
      <view class="swipe-content">
        <view
          class="event-checkbox"
          :class="{ checked: event.completed }"
          @tap.stop="emit('toggle')"
        >
          <text v-if="event.completed" class="check-mark">✓</text>
        </view>

        <view class="event-main" @tap="onMainTap">
          <view class="time-col">
            <text class="time-text">{{ formatTime(event.start_time) }}</text>
            <text v-if="event.end_time" class="time-end">{{
              formatTime(event.end_time)
            }}</text>
          </view>
          <view class="info-col">
            <text class="event-title">{{ event.title }}</text>
            <text
              v-if="event.repeat_type && event.repeat_type !== 'none'"
              class="repeat-badge"
            >
              {{ repeatLabel(event.repeat_type) }}
            </text>
            <text v-if="showNote && event.note" class="event-note">{{
              event.note
            }}</text>
          </view>
          <text class="item-arrow">›</text>
        </view>
      </view>

      <view class="swipe-actions">
        <view class="action-btn edit-btn" @tap.stop="emit('edit')">
          <text>编辑</text>
        </view>
        <view class="action-btn delete-btn" @tap.stop="emit('delete')">
          <text>删除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { formatTime, repeatTypeLabel } from "@/utils/date.js";

const ACTION_WIDTH = uni.upx2px(280);

const props = defineProps({
  event: { type: Object, required: true },
  open: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  showNote: { type: Boolean, default: false },
});

const emit = defineEmits(["open", "close", "edit", "delete", "toggle", "click"]);

const offset = ref(0);
const isDragging = ref(false);
let startX = 0;
let startY = 0;
let baseOffset = 0;
let dragging = false;
let horizontalLock = false;

const trackStyle = computed(() => ({
  transform: `translateX(${offset.value}px)`,
}));

watch(
  () => props.open,
  (val) => {
    offset.value = val ? -ACTION_WIDTH : 0;
  },
);

function repeatLabel(type) {
  return repeatTypeLabel(type);
}

function onMainTap() {
  if (props.disabled) return;
  if (offset.value < 0) {
    offset.value = 0;
    emit("close");
    return;
  }
  emit("click", props.event);
}

function onTouchStart(e) {
  if (props.disabled) return;
  startX = e.touches[0].clientX;
  startY = e.touches[0].clientY;
  baseOffset = props.open ? -ACTION_WIDTH : 0;
  dragging = true;
  isDragging.value = true;
  horizontalLock = false;
}

function onTouchMove(e) {
  if (!dragging || props.disabled) return;

  const dx = e.touches[0].clientX - startX;
  const dy = e.touches[0].clientY - startY;

  if (!horizontalLock) {
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 6) {
      horizontalLock = true;
    } else if (Math.abs(dy) > 6) {
      dragging = false;
      isDragging.value = false;
      return;
    }
  }

  let next = baseOffset + dx;
  next = Math.min(0, Math.max(-ACTION_WIDTH, next));
  offset.value = next;
}

function onTouchEnd() {
  if (!dragging) return;
  dragging = false;
  isDragging.value = false;
  horizontalLock = false;

  if (offset.value < -ACTION_WIDTH / 2) {
    offset.value = -ACTION_WIDTH;
    emit("open");
  } else {
    offset.value = 0;
    emit("close");
  }
}
</script>

<style lang="scss" scoped>
@import "./EventSwipeItem.scss";
</style>
