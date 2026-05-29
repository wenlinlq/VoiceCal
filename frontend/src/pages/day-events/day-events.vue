<template>
  <view class="page-day-events page-shell">
    <view class="page-slide" :class="{ active: pageActive, leaving: pageLeaving }">
      <view class="nav-bar">
        <view class="nav-back" @tap="goBack">
          <text class="back-icon">‹</text>
          <text class="back-text">返回</text>
        </view>
        <text class="nav-title">{{ pageTitle }}</text>
        <view class="nav-placeholder" />
      </view>

      <scroll-view scroll-y class="event-scroll" :show-scrollbar="false">
        <view v-if="events.length === 0" class="empty-state">
          <text class="empty-text">当日暂无日程</text>
          <text class="empty-hint">长按麦克风添加事件</text>
        </view>

        <view v-else class="list-body">
          <view
            v-for="event in events"
            :key="event.id"
            class="event-item"
            @tap="onEventClick(event)"
          >
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
              <text v-if="event.note" class="event-note">{{ event.note }}</text>
            </view>
            <text class="item-arrow">›</text>
          </view>
        </view>
      </scroll-view>

      <GlobalVoice />
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useCalendarStore } from "@/store/modules/calendar.js";
import {
  formatTime,
  formatDisplayDate,
  repeatTypeLabel,
} from "@/utils/date.js";
import { usePageSlideNav } from "@/composables/usePageSlideNav.js";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";

const { pageActive, pageLeaving, goBack, ANIM_DURATION } = usePageSlideNav({
  getFallbackUrl: () => "/pages/index/index",
});

const calendarStore = useCalendarStore();
const date = ref("");

const events = computed(() => {
  if (!date.value) return [];
  return calendarStore.events
    .filter((e) => e.start_time.startsWith(date.value))
    .sort((a, b) => a.start_time.localeCompare(b.start_time));
});

const pageTitle = computed(() => {
  if (!date.value) return "今日事件";
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return date.value === todayStr
    ? "今日事件"
    : `${formatDisplayDate(date.value)} 事件`;
});

onLoad((query) => {
  date.value = query.date || calendarStore.currentDate;
});

function repeatLabel(type) {
  return repeatTypeLabel(type);
}

function onEventClick(event) {
  uni.navigateTo({
    url: `/pages/event-detail/event-detail?id=${event.id}&from=day-events&date=${encodeURIComponent(date.value)}`,
    animationType: "slide-in-right",
    animationDuration: ANIM_DURATION,
  });
}
</script>

<style lang="scss" scoped>
@import "./day-events.scss";
</style>
