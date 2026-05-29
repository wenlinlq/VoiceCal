<template>
  <view class="page-day-events page-shell">
    <view class="page-slide" :class="{ active: pageActive, leaving: pageLeaving }" :style="pageBottomStyle">
      <view class="nav-bar" :style="navBarStyle">
        <view class="nav-back" @tap="goBack">
          <text class="back-icon">‹</text>
          <text class="back-text">返回</text>
        </view>
        <text class="nav-title">{{ pageTitle }}</text>
        <view class="nav-placeholder" />
      </view>

      <scroll-view scroll-y class="event-scroll" :show-scrollbar="false">
        <EventItemsList
          :events="events"
          show-note
          @item-click="onEventClick"
        />
      </scroll-view>

      <GlobalVoice />
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { formatDisplayDate } from "@/utils/date.js";
import { usePageSlideNav } from "@/composables/usePageSlideNav.js";
import { useMpSafeArea } from "@/composables/useMpSafeArea.js";
import EventItemsList from "@/components/EventItemsList/EventItemsList.vue";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";

const { pageActive, pageLeaving, goBack, ANIM_DURATION } = usePageSlideNav({
  getFallbackUrl: () => "/pages/index/index",
});

const calendarStore = useCalendarStore();
const { navBarStyle, pageBottomStyle } = useMpSafeArea();
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
