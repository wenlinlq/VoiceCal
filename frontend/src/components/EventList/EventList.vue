<template>
  <view class="event-list">
    <view class="list-header">
      <view class="header-left">
        <text class="header-title">{{ headerTitle }}</text>
      </view>
      <view v-if="events.length > 0" class="header-more" @tap="$emit('more')">
        <text>更多</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <view v-if="events.length === 0" class="empty-state">
      <text class="empty-text">当日暂无日程</text>
      <text class="empty-hint">长按麦克风添加事件</text>
    </view>

    <view v-else class="list-body">
      <view
        v-for="event in events"
        :key="event.id"
        class="event-item"
        @tap="onItemClick(event)"
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
        </view>
        <text class="item-arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import {
  formatTime,
  formatDisplayDate,
  repeatTypeLabel,
} from "@/utils/date.js";

const props = defineProps({
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["itemClick", "more"]);

const headerTitle = computed(() => {
  if (!props.currentDate) return "今日事件";
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return props.currentDate === todayStr
    ? "今日事件"
    : `${formatDisplayDate(props.currentDate)} 事件`;
});

function repeatLabel(type) {
  return repeatTypeLabel(type);
}

function onItemClick(event) {
  if (props.disabled) return;
  emit("itemClick", event);
}
</script>

<style lang="scss" scoped>
@import "./EventList.scss";
</style>
