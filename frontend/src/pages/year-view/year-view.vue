<template>
  <view class="page-year">
    <view class="toolbar">
      <view class="toolbar-actions">
        <view class="icon-btn" @tap="goAdd">
          <view class="icon-plus" />
        </view>
        <view class="icon-btn" @tap="goToday">
          <view class="icon-calendar">
            <view class="cal-dot" />
          </view>
        </view>
        <view class="icon-btn" @tap="onMenu">
          <view class="icon-more">
            <view class="dot" />
            <view class="dot" />
            <view class="dot" />
          </view>
        </view>
      </view>
    </view>

    <view class="year-header">
      <view class="year-header-main">
        <text class="year-title">{{ displayYear }}</text>
        <view class="legend legend-vertical">
          <view class="legend-item">
            <view class="legend-line red" />
            <text>{{ lunarYearLabel }}</text>
          </view>
          <view class="legend-item">
            <view class="legend-line blue" />
            <text>农历初一</text>
          </view>
        </view>
      </view>
    </view>

    <view class="year-body" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <view class="slide-viewport">
        <view v-if="!yearSlide.active" class="slide-stage">
          <scroll-view scroll-y class="year-scroll" :show-scrollbar="false">
            <view class="months-grid">
              <MiniMonthCard
                v-for="m in 12"
                :key="`${viewYear}-${m}`"
                :year="viewYear"
                :month-index="m - 1"
                :events="calendarStore.events"
                :current-date="calendarStore.currentDate"
                :is-current-month="
                  m - 1 === calendarStore.viewMonth &&
                  viewYear === calendarStore.viewYear
                "
                @select="selectMonth(m - 1)"
              />
            </view>
          </scroll-view>
        </view>

        <view v-else class="slide-stage">
          <view
            class="year-panel is-leaving"
            :class="`dir-${yearSlide.direction}`"
          >
            <scroll-view scroll-y class="year-scroll" :show-scrollbar="false">
              <view class="months-grid">
                <MiniMonthCard
                  v-for="m in 12"
                  :key="`l-${yearSlide.leaving}-${m}`"
                  :year="yearSlide.leaving"
                  :month-index="m - 1"
                  :events="calendarStore.events"
                  :current-date="calendarStore.currentDate"
                  :is-current-month="false"
                  @select="selectMonth(m - 1)"
                />
              </view>
            </scroll-view>
          </view>
          <view
            class="year-panel is-entering"
            :class="[`dir-${yearSlide.direction}`, { run: yearSlide.run }]"
          >
            <scroll-view scroll-y class="year-scroll" :show-scrollbar="false">
              <view class="months-grid">
                <MiniMonthCard
                  v-for="m in 12"
                  :key="`e-${yearSlide.entering}-${m}`"
                  :year="yearSlide.entering"
                  :month-index="m - 1"
                  :events="calendarStore.events"
                  :current-date="calendarStore.currentDate"
                  :is-current-month="false"
                  @select="selectMonth(m - 1)"
                />
              </view>
            </scroll-view>
          </view>
        </view>
      </view>
    </view>

    <GlobalVoice />
  </view>
</template>

<script setup>
import { ref, computed, nextTick } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { formatDate } from "@/utils/date.js";
import { getLunarYearLabel } from "@/utils/lunar.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import MiniMonthCard from "@/components/MiniMonthCard/MiniMonthCard.vue";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";

const calendarStore = useCalendarStore();
const viewYear = ref(new Date().getFullYear());
const touchStartX = ref(0);
const touchStartY = ref(0);
const isAnimating = ref(false);

const yearSlide = ref({
  active: false,
  run: false,
  direction: "next",
  leaving: 0,
  entering: 0,
});

const SLIDE_DURATION = 320;

const displayYear = computed(() => {
  return yearSlide.value.active ? yearSlide.value.entering : viewYear.value;
});

const lunarYearLabel = computed(() => getLunarYearLabel(displayYear.value));

onLoad((query) => {
  if (query.year) {
    viewYear.value = Number(query.year);
  } else {
    viewYear.value = calendarStore.viewYear;
  }
});

function animateYearChange(delta) {
  if (isAnimating.value) return;

  const targetYear = viewYear.value + delta;
  const direction = delta > 0 ? "next" : "prev";

  isAnimating.value = true;
  yearSlide.value = {
    active: true,
    run: false,
    direction,
    leaving: viewYear.value,
    entering: targetYear,
  };

  nextTick(() => {
    requestAnimationFrame(() => {
      yearSlide.value.run = true;
    });
  });

  setTimeout(() => {
    viewYear.value = targetYear;
    yearSlide.value = {
      active: false,
      run: false,
      direction: "next",
      leaving: 0,
      entering: 0,
    };
    isAnimating.value = false;
  }, SLIDE_DURATION);
}

function onTouchStart(e) {
  if (isAnimating.value) return;
  touchStartX.value = e.changedTouches[0].clientX;
  touchStartY.value = e.changedTouches[0].clientY;
}

function onTouchEnd(e) {
  if (isAnimating.value) return;
  const endX = e.changedTouches[0].clientX;
  const endY = e.changedTouches[0].clientY;
  const diffX = endX - touchStartX.value;
  const diffY = endY - touchStartY.value;

  if (Math.abs(diffX) < 60 || Math.abs(diffX) < Math.abs(diffY)) return;
  animateYearChange(diffX < 0 ? 1 : -1);
}

function selectMonth(month) {
  const year = yearSlide.value.active
    ? yearSlide.value.entering
    : viewYear.value;
  calendarStore.setViewMonth(year, month);
  uni.navigateBack();
}

function goToday() {
  const now = new Date();
  const today = formatDate(now);
  calendarStore.setCurrentDate(today);
  calendarStore.setViewMonth(now.getFullYear(), now.getMonth());
  viewYear.value = now.getFullYear();
  uni.navigateBack();
}

function goAdd() {
  uni.navigateBack({
    success: () => {
      setTimeout(() => {
        uni.$emit("calendar:openCreate");
      }, 300);
    },
  });
}

function onMenu() {
  uni.showActionSheet({
    itemList: ["设置", "使用引导"],
    success: (res) => {
      if (res.tapIndex === 0) {
        uni.navigateTo({ url: "/pages/settings/settings" });
      } else if (res.tapIndex === 1) {
        uni.showModal({
          title: "语音指令示例",
          content:
            "「明天下午3点开会」— 添加日程\n「今天有什么安排」— 查看今日事件\n「删除今天下午3点的会」— 删除事件",
          showCancel: false,
        });
      }
    },
  });
}
</script>

<style lang="scss" scoped>
@import "./year-view.scss";
</style>
