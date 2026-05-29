<template>
  <view class="calendar-view" :class="{ disabled }">
    <view class="toolbar">
      <view class="toolbar-actions">
        <view class="icon-btn" @tap.stop="emit('add')">
          <view class="icon-plus" />
        </view>
        <view class="icon-btn" @tap.stop="onTodayTap">
          <view class="icon-calendar">
            <view class="cal-dot" />
          </view>
        </view>
        <view class="icon-btn" @tap.stop="emit('menu')">
          <view class="icon-more">
            <view class="dot" />
            <view class="dot" />
            <view class="dot" />
          </view>
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

    <view class="month-view" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <view class="slide-viewport">
        <view v-if="!slideAnim.active" class="slide-stage">
          <view class="month-panel is-current">
            <CalendarMonthGrid
              :year="viewYear"
              :month="viewMonth"
              :events="events"
              :current-date="currentDate"
              @day-click="onDayClick"
            />
          </view>
        </view>

        <view v-else class="slide-stage">
          <view
            class="month-panel is-leaving"
            :class="`dir-${slideAnim.direction}`"
          >
            <CalendarMonthGrid
              :year="slideAnim.leaving.year"
              :month="slideAnim.leaving.month"
              :events="events"
              :current-date="currentDate"
              @day-click="onDayClick"
            />
          </view>
          <view
            class="month-panel is-entering"
            :class="[`dir-${slideAnim.direction}`, { run: slideAnim.run }]"
          >
            <CalendarMonthGrid
              :year="slideAnim.entering.year"
              :month="slideAnim.entering.month"
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
import { ref, computed, nextTick } from "vue";
import { shiftMonth, getDaysOffsetLabel } from "@/utils/date.js";
import CalendarMonthGrid from "@/components/CalendarMonthGrid/CalendarMonthGrid.vue";

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

const touchStartX = ref(0);
const isAnimating = ref(false);
const slideAnim = ref({
  active: false,
  run: false,
  direction: "next",
  leaving: { year: 0, month: 0 },
  entering: { year: 0, month: 0 },
});

const SLIDE_DURATION = 320;

const daysOffsetLabel = computed(() => getDaysOffsetLabel(props.currentDate));

function onDayClick(day) {
  if (props.disabled) return;
  emit("dateClick", day.date);
  emit("dateChange", day.date);
}

function onTodayTap() {
  if (props.disabled) return;
  emit("today");
}

function openYearView() {
  if (props.disabled) return;
  uni.navigateTo({
    url: `/pages/year-view/year-view?year=${props.viewYear}`,
  });
}

function animateMonthChange(delta) {
  if (props.disabled || isAnimating.value) return;

  const target = shiftMonth(props.viewYear, props.viewMonth, delta);
  const direction = delta > 0 ? "next" : "prev";

  isAnimating.value = true;
  slideAnim.value = {
    active: true,
    run: false,
    direction,
    leaving: { year: props.viewYear, month: props.viewMonth },
    entering: { year: target.year, month: target.month },
  };

  nextTick(() => {
    requestAnimationFrame(() => {
      slideAnim.value.run = true;
    });
  });

  setTimeout(() => {
    emit("monthChange", target.year, target.month);
    slideAnim.value = {
      active: false,
      run: false,
      direction: "next",
      leaving: { year: 0, month: 0 },
      entering: { year: 0, month: 0 },
    };
    isAnimating.value = false;
  }, SLIDE_DURATION);
}

function onTouchStart(e) {
  if (props.disabled || isAnimating.value) return;
  touchStartX.value = e.changedTouches[0].clientX;
}

function onTouchEnd(e) {
  if (props.disabled || isAnimating.value) return;
  const diff = e.changedTouches[0].clientX - touchStartX.value;
  if (Math.abs(diff) < 60) return;
  // 向左滑 → 下个月（内容向左移出）
  animateMonthChange(diff < 0 ? 1 : -1);
}
</script>

<style lang="scss" scoped>
@import "./CalendarView.scss";
</style>
