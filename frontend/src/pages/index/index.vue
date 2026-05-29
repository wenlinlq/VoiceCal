<template>
  <view class="page-index">
    <CalendarView
      :events="calendarStore.events"
      :current-date="calendarStore.currentDate"
      :view-year="calendarStore.viewYear"
      :view-month="calendarStore.viewMonth"
      :disabled="isVoiceActive"
      @date-change="onDateChange"
      @date-click="onDateChange"
      @month-change="onMonthChange"
      @add="openCreateForm"
      @today="goToday"
      @menu="onMenu"
    />

    <EventList
      :events="calendarStore.todayEvents"
      :current-date="calendarStore.currentDate"
      :disabled="isVoiceActive"
      @item-click="onEventClick"
      @more="onMoreEvents"
    />

    <GlobalVoice />

    <ConfirmDialog
      :visible="confirmStore.visible"
      :message="confirmStore.message"
      :event="confirmStore.event"
      @confirm="onConfirm"
      @cancel="onCancel"
    />

    <EventFormModal
      :visible="showCreateForm"
      :default-date="calendarStore.currentDate"
      @close="showCreateForm = false"
      @save="onCreateEvent"
    />
  </view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { formatDate } from "@/utils/date.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { useConfirmStore } from "@/store/modules/confirm.js";
import { useVoiceInteraction } from "@/composables/useVoiceInteraction.js";
import CalendarView from "@/components/CalendarView/CalendarView.vue";
import EventList from "@/components/EventList/EventList.vue";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";
import ConfirmDialog from "@/components/ConfirmDialog/ConfirmDialog.vue";
import EventFormModal from "@/components/EventFormModal/EventFormModal.vue";

const calendarStore = useCalendarStore();
const confirmStore = useConfirmStore();
const { isVoiceActive } = useVoiceInteraction();
const showCreateForm = ref(false);

onMounted(() => {
  uni.$on("calendar:openCreate", openCreateForm);
});

onUnmounted(() => {
  uni.$off("calendar:openCreate", openCreateForm);
});

function onDateChange(date) {
  calendarStore.setCurrentDate(date);
}

function onMonthChange(year, month) {
  calendarStore.setViewMonth(year, month);
}

const PAGE_ANIM_DURATION = 320;

function onEventClick(event) {
  uni.navigateTo({
    url: `/pages/event-detail/event-detail?id=${event.id}&from=index`,
    animationType: "slide-in-right",
    animationDuration: PAGE_ANIM_DURATION,
  });
}

function onMoreEvents() {
  if (isVoiceActive.value) return;
  uni.navigateTo({
    url: `/pages/day-events/day-events?date=${calendarStore.currentDate}`,
    animationType: "slide-in-right",
    animationDuration: PAGE_ANIM_DURATION,
  });
}

function openCreateForm() {
  showCreateForm.value = true;
}

function goToday() {
  const today = formatDate(new Date());
  const now = new Date();
  calendarStore.setCurrentDate(today);
  calendarStore.setViewMonth(now.getFullYear(), now.getMonth());
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

async function onCreateEvent(data) {
  await calendarStore.addEvent(data);
  showCreateForm.value = false;
  calendarStore.setCurrentDate(data.start_time.slice(0, 10));
  uni.showToast({ title: "日程已创建", icon: "success" });
}

function onConfirm() {
  confirmStore.confirm();
}

function onCancel() {
  confirmStore.cancel();
}
</script>

<style lang="scss" scoped>
@import "./index.scss";
</style>
