<template>
  <view class="event-list">
    <view class="list-header">
      <view class="header-left">
        <text class="header-title">{{ headerTitle }}</text>
      </view>
      <view class="header-more" @tap="$emit('more')">
        <text>更多</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <EventItemsList
      :events="events"
      :disabled="disabled"
      @item-click="onItemClick"
    />
  </view>
</template>

<script setup>
import { computed } from "vue";
import { formatDisplayDate } from "@/utils/date.js";
import EventItemsList from "@/components/EventItemsList/EventItemsList.vue";

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

function onItemClick(event) {
  if (props.disabled) return;
  emit("itemClick", event);
}
</script>

<style lang="scss" scoped>
@import "./EventList.scss";
</style>
