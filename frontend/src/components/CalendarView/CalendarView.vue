<template>
  <view class="calendar-view" :class="{ disabled }">
    <view class="nav-bar" :style="navRowStyle">
      <view class="toolbar-actions">
        <view class="icon-btn" @tap.stop="emit('menu')">
          <view class="icon-more">
            <view class="dot" />
            <view class="dot" />
            <view class="dot" />
          </view>
        </view>
        <view class="icon-btn" @tap.stop="emit('add')">
          <view class="icon-plus" />
        </view>
      </view>
    </view>

    <view class="month-row">
      <view class="month-title-wrap" @tap="openYearView">
        <text class="month-title">{{ viewYear }} / {{ viewMonth + 1 }}</text>
        <text class="title-chevron">›</text>
      </view>
      <text class="date-offset">{{ daysOffsetLabel }}</text>
    </view>

    <view
      class="month-view"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      @touchcancel="onTouchEnd"
    >
      <view class="slide-viewport">
        <view class="slide-track" :style="trackStyle">
          <view
            v-for="panel in monthPanels"
            :key="panel.key"
            class="month-panel"
            :style="panelStyle"
          >
            <CalendarMonthGrid
              :year="panel.year"
              :month="panel.month"
              :events="events"
              :current-date="currentDate"
              @day-click="onDayClick"
            />
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, onMounted, getCurrentInstance } from "vue";
import { shiftMonth, getDaysOffsetLabel } from "@/utils/date.js";
import { useMpSafeArea } from "@/composables/useMpSafeArea.js";
import CalendarMonthGrid from "@/components/CalendarMonthGrid/CalendarMonthGrid.vue";

const { navRowStyle } = useMpSafeArea();

const props = defineProps({
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: "" },
  viewYear: { type: Number, required: true },
  viewMonth: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits([
  "dateChange",
  "dateClick",
  "monthChange",
  "add",
  "today",
  "menu",
]);

const instance = getCurrentInstance();
const viewportWidth = ref(0);
const dragOffset = ref(0);
const isDragging = ref(false);
const isSnapping = ref(false);
const touchStartX = ref(0);
const touchStartOffset = ref(0);

const SWIPE_THRESHOLD = 0.22;
const SNAP_DURATION = 280;

const monthPanels = computed(() => {
  const prev = shiftMonth(props.viewYear, props.viewMonth, -1);
  const next = shiftMonth(props.viewYear, props.viewMonth, 1);
  return [
    { key: `p-${prev.year}-${prev.month}`, ...prev },
    { key: `c-${props.viewYear}-${props.viewMonth}`, year: props.viewYear, month: props.viewMonth },
    { key: `n-${next.year}-${next.month}`, ...next },
  ];
});

const daysOffsetLabel = computed(() => getDaysOffsetLabel(props.currentDate));

const trackStyle = computed(() => {
  const w = viewportWidth.value || 375;
  const x = -w + dragOffset.value;
  return {
    width: `${w * 3}px`,
    transform: `translateX(${x}px)`,
    transition: isDragging.value || !isSnapping.value
      ? "none"
      : `transform ${SNAP_DURATION}ms cubic-bezier(0.25, 0.8, 0.25, 1)`,
  };
});

const panelStyle = computed(() => {
  const w = viewportWidth.value || 375;
  return {
    width: `${w}px`,
    flex: `0 0 ${w}px`,
  };
});

function measureViewport() {
  uni
    .createSelectorQuery()
    .in(instance?.proxy)
    .select(".slide-viewport")
    .boundingClientRect((rect) => {
      if (rect?.width) viewportWidth.value = rect.width;
    })
    .exec();
}

onMounted(() => {
  measureViewport();
});

watch(
  () => [props.viewYear, props.viewMonth],
  () => {
    dragOffset.value = 0;
    isSnapping.value = false;
  },
);

function onDayClick(day) {
  if (props.disabled) return;
  emit("dateClick", day.date);
  emit("dateChange", day.date);
}

function openYearView() {
  if (props.disabled) return;
  uni.navigateTo({
    url: `/pages/year-view/year-view?year=${props.viewYear}`,
  });
}

function clampDrag(offset) {
  const w = viewportWidth.value || 375;
  const max = w * 0.85;
  return Math.max(-max, Math.min(max, offset));
}

function onTouchStart(e) {
  if (props.disabled || isSnapping.value) return;
  if (!viewportWidth.value) measureViewport();
  isDragging.value = true;
  touchStartX.value = e.touches[0].clientX;
  touchStartOffset.value = dragOffset.value;
}

function onTouchMove(e) {
  if (!isDragging.value || props.disabled) return;
  const delta = e.touches[0].clientX - touchStartX.value;
  dragOffset.value = clampDrag(touchStartOffset.value + delta);
}

function finishSnap(targetOffset, deltaMonth) {
  isDragging.value = false;
  isSnapping.value = true;
  dragOffset.value = targetOffset;

  setTimeout(() => {
    if (deltaMonth !== 0) {
      const target = shiftMonth(props.viewYear, props.viewMonth, deltaMonth);
      emit("monthChange", target.year, target.month);
    }
    dragOffset.value = 0;
    isSnapping.value = false;
  }, SNAP_DURATION);
}

function onTouchEnd() {
  if (!isDragging.value || props.disabled) return;

  const w = viewportWidth.value || 375;
  const ratio = dragOffset.value / w;

  if (ratio <= -SWIPE_THRESHOLD) {
    finishSnap(-w, 1);
    return;
  }
  if (ratio >= SWIPE_THRESHOLD) {
    finishSnap(w, -1);
    return;
  }
  finishSnap(0, 0);
}
</script>

<style lang="scss" scoped>
@import "./CalendarView.scss";
</style>
