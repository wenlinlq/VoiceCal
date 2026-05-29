<template>
  <view v-if="mounted" class="dtp-overlay" :class="{ active }">
    <view class="dtp-mask" @tap="requestClose" />
    <view class="dtp-panel" @tap.stop>
      <text class="dtp-title">{{ title }}</text>
      <text class="dtp-preview">{{ previewText }}</text>

      <picker-view
        v-if="wheelReady"
        :key="pickerKey"
        class="dtp-wheels"
        :value="indexes"
        indicator-class="dtp-indicator"
        indicator-style="height: 40px;"
        @change="onWheelChange"
      >
        <picker-view-column>
          <view
            v-for="(item, idx) in dateOptions"
            :key="item.value"
            class="dtp-wheel-item"
            :class="{ active: idx === indexes[0] }"
          >
            <text>{{ item.label }}</text>
          </view>
        </picker-view-column>
        <picker-view-column class="dtp-col-hour">
          <view
            v-for="(item, idx) in hourOptions"
            :key="item"
            class="dtp-wheel-item"
            :class="{ active: idx === indexes[1] }"
          >
            <text class="wheel-num">{{ item }}</text>
            <text class="wheel-unit">时</text>
          </view>
        </picker-view-column>
        <picker-view-column class="dtp-col-minute">
          <view
            v-for="(item, idx) in minuteOptions"
            :key="item"
            class="dtp-wheel-item"
            :class="{ active: idx === indexes[2] }"
          >
            <text class="wheel-num">{{ item }}</text>
            <text class="wheel-unit">分</text>
          </view>
        </picker-view-column>
      </picker-view>

      <view class="dtp-lunar-row">
        <text class="dtp-lunar-label">农历</text>
        <switch :checked="useLunar" color="#1a73e8" @change="onLunarToggle" />
      </view>

      <view class="dtp-actions">
        <view class="dtp-btn dtp-btn-cancel" @tap="requestClose">
          <text>取消</text>
        </view>
        <view class="dtp-btn dtp-btn-confirm" @tap="onConfirm">
          <text>确定</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from "vue";
import {
  formatDate,
  formatDateTimeValue,
  formatDateTimePreview,
  parseDateTime,
  buildDateWheelOptions,
} from "@/utils/date.js";
import { solar2lunar } from "@/utils/lunar.js";

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: "选择时间" },
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "close", "confirm"]);

const ANIM_DURATION = 320;

const DATE_RANGE_BEFORE = 180;
const DATE_RANGE_AFTER = 730;

const mounted = ref(false);
const active = ref(false);
const dateOptions = ref([]);
const hourOptions = Array.from({ length: 24 }, (_, i) =>
  String(i).padStart(2, "0"),
);
const minuteOptions = Array.from({ length: 60 }, (_, i) =>
  String(i).padStart(2, "0"),
);

const indexes = ref([0, 9, 0]);
const wheelReady = ref(false);
const pickerKey = ref(0);
const useLunar = ref(false);
const draftValue = ref("");

let hideTimer = null;
let closeTimer = null;

const previewText = computed(() => {
  if (!draftValue.value) return "";
  if (!useLunar.value) {
    return formatDateTimePreview(draftValue.value);
  }
  const date = parseDateTime(draftValue.value);
  const lunar = solar2lunar(
    date.getFullYear(),
    date.getMonth() + 1,
    date.getDate(),
  );
  const time = formatDateTimePreview(draftValue.value).split(" ").pop();
  return `农历${lunar.monthCn}月${lunar.dayCn} ${time}`;
});

watch(
  () => props.visible,
  async (val) => {
    clearTimers();
    if (val) {
      wheelReady.value = false;
      initPicker(props.modelValue || formatDateTimeValue(new Date()));
      mounted.value = true;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          active.value = true;
        });
      });
      await nextTick();
      pickerKey.value += 1;
      wheelReady.value = true;
    } else if (mounted.value) {
      wheelReady.value = false;
      active.value = false;
      hideTimer = setTimeout(() => {
        mounted.value = false;
      }, ANIM_DURATION);
    }
  },
);

watch(wheelReady, async (ready) => {
  if (!ready) return;
  await nextTick();
  const current = [...indexes.value];
  indexes.value = [0, 0, 0];
  await nextTick();
  indexes.value = current;
});

function clearTimers() {
  if (hideTimer) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }
}

function initPicker(value) {
  const date = parseDateTime(value);
  dateOptions.value = buildDateWheelOptions(
    date,
    DATE_RANGE_BEFORE,
    DATE_RANGE_AFTER,
  );

  const dateStr = formatDate(date);
  let dateIdx = dateOptions.value.findIndex((item) => item.value === dateStr);
  if (dateIdx < 0) dateIdx = DATE_RANGE_BEFORE;

  indexes.value = [dateIdx, date.getHours(), date.getMinutes()];
  draftValue.value = formatDateTimeValue(date);
  useLunar.value = false;
}

function syncDraftValue(nextIndexes = indexes.value) {
  const dateItem = dateOptions.value[nextIndexes[0]];
  if (!dateItem) return;
  const date = parseDateTime(`${dateItem.value} 00:00:00`);
  date.setHours(nextIndexes[1], nextIndexes[2], 0, 0);
  draftValue.value = formatDateTimeValue(date);
}

function onWheelChange(e) {
  indexes.value = e.detail.value;
  syncDraftValue(indexes.value);
}

function onLunarToggle(e) {
  useLunar.value = e.detail.value;
}

function requestClose() {
  if (!active.value) return;
  active.value = false;
  closeTimer = setTimeout(() => {
    mounted.value = false;
    emit("close");
  }, ANIM_DURATION);
}

function onConfirm() {
  emit("update:modelValue", draftValue.value);
  emit("confirm", draftValue.value);
  requestClose();
}

onBeforeUnmount(() => {
  clearTimers();
});
</script>

<style lang="scss" scoped>
.dtp-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
}

.dtp-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.32s ease;
}

.dtp-overlay.active .dtp-mask {
  background-color: rgba(0, 0, 0, 0.45);
}

.dtp-panel {
  position: absolute;
  left: 50%;
  top: 50%;
  width: calc(100% - 48px);
  max-width: 360px;
  background: #fff;
  border-radius: 20px;
  padding: 20px 16px 16px;
  box-sizing: border-box;
  opacity: 0;
  transform: translate(-50%, -50%);
  transition: opacity 0.32s ease;
}

.dtp-overlay.active .dtp-panel {
  opacity: 1;
}

.dtp-title {
  display: block;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.dtp-preview {
  display: block;
  text-align: center;
  font-size: 14px;
  color: #888;
  margin-bottom: 12px;
}

.dtp-wheels {
  width: 100%;
  height: 200px;
}

:deep(.uni-picker-view-indicator),
:deep(.dtp-indicator) {
  height: 40px;
  box-sizing: border-box;
}

:deep(.uni-picker-view-content .dtp-wheel-item) {
  height: var(--picker-view-column-indicator-height, 40px);
  min-height: var(--picker-view-column-indicator-height, 40px);
  max-height: var(--picker-view-column-indicator-height, 40px);
  line-height: var(--picker-view-column-indicator-height, 40px);
  box-sizing: border-box;
}

.dtp-wheel-item {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--picker-view-column-indicator-height, 40px);
  line-height: var(--picker-view-column-indicator-height, 40px);
  font-size: 16px;
  color: #bbb;
  box-sizing: border-box;
  overflow: hidden;

  &.active {
    color: #1a73e8;
    font-weight: 600;
  }

  uni-text,
  text {
    line-height: inherit;
  }
}

.wheel-num {
  min-width: 2em;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.wheel-unit {
  width: 1em;
  flex-shrink: 0;
  opacity: 0;
}

.dtp-wheel-item.active .wheel-unit {
  opacity: 1;
}

.dtp-lunar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 8px 4px;
}

.dtp-lunar-label {
  font-size: 16px;
  color: #333;
}

.dtp-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.dtp-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 500;
}

.dtp-btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.dtp-btn-confirm {
  background: #1a73e8;
  color: #fff;
}

/* #ifndef H5 */
.dtp-panel {
  width: calc(100% - 96rpx);
  max-width: 640rpx;
  border-radius: 40rpx;
  padding: 40rpx 32rpx 32rpx;
}

.dtp-title {
  font-size: 36rpx;
  margin-bottom: 16rpx;
}

.dtp-preview {
  font-size: 28rpx;
  margin-bottom: 24rpx;
}

.dtp-wheels {
  height: 400rpx;
}

:deep(.uni-picker-view-indicator),
:deep(.dtp-indicator) {
  height: 80rpx;
}

:deep(.uni-picker-view-content .dtp-wheel-item) {
  height: var(--picker-view-column-indicator-height, 80rpx);
  min-height: var(--picker-view-column-indicator-height, 80rpx);
  max-height: var(--picker-view-column-indicator-height, 80rpx);
  line-height: var(--picker-view-column-indicator-height, 80rpx);
}

.dtp-wheel-item {
  height: var(--picker-view-column-indicator-height, 80rpx);
  line-height: var(--picker-view-column-indicator-height, 80rpx);
  font-size: 32rpx;
}

.dtp-lunar-row {
  padding: 24rpx 16rpx 8rpx;
}

.dtp-lunar-label {
  font-size: 32rpx;
}

.dtp-actions {
  gap: 24rpx;
  margin-top: 24rpx;
}

.dtp-btn {
  height: 88rpx;
  border-radius: 44rpx;
  font-size: 32rpx;
}
/* #endif */
</style>
