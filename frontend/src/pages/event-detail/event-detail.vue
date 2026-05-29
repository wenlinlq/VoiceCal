<template>
  <view class="page-detail page-shell">
    <view class="page-slide" :class="{ active: pageActive, leaving: pageLeaving }">
      <view class="nav-bar">
        <view class="nav-back" @tap="goBack">
          <text class="back-icon">‹</text>
          <text class="back-text">返回</text>
        </view>
        <text class="nav-title">事件详情</text>
        <view class="nav-placeholder" />
      </view>

      <scroll-view scroll-y class="detail-scroll" :show-scrollbar="false">
        <view v-if="event" class="detail-content">
          <view class="title-section">
            <text class="event-title">{{ event.title }}</text>
          </view>

          <view class="info-card">
            <view class="info-row">
              <text class="info-label">时间</text>
              <text class="info-value">{{ timeRange }}</text>
            </view>
            <view class="info-row">
              <text class="info-label">日期</text>
              <text class="info-value">{{ displayDate }}</text>
            </view>
            <view class="info-row">
              <text class="info-label">重复</text>
              <text class="info-value">{{ repeatLabel }}</text>
            </view>
            <view v-if="event.note" class="info-row">
              <text class="info-label">备注</text>
              <text class="info-value">{{ event.note }}</text>
            </view>
          </view>

          <view class="action-bar">
            <view class="action-btn edit-btn" @tap="onEdit">
              <text>编辑</text>
            </view>
            <view class="action-btn delete-btn" @tap="onDelete">
              <text>删除</text>
            </view>
          </view>
        </view>

        <view v-else class="not-found">
          <text class="not-found-text">事件不存在</text>
          <view class="back-btn" @tap="goBack">
            <text>返回</text>
          </view>
        </view>
      </scroll-view>

      <GlobalVoice />

      <ConfirmDialog
        :visible="showDeleteConfirm"
        variant="danger"
        title="删除日程"
        message="确认删除这个日程吗？删除后无法恢复。"
        confirm-text="删除"
        :event="event"
        @confirm="confirmDelete"
        @cancel="showDeleteConfirm = false"
      />

      <EventFormModal
        :visible="showEditForm"
        mode="edit"
        :event-data="event"
        @close="showEditForm = false"
        @save="onSaveEdit"
      />
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { formatTime, formatDisplayDate, repeatTypeLabel } from "@/utils/date.js";
import { usePageSlideNav } from "@/composables/usePageSlideNav.js";
import ConfirmDialog from "@/components/ConfirmDialog/ConfirmDialog.vue";
import EventFormModal from "@/components/EventFormModal/EventFormModal.vue";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";

const calendarStore = useCalendarStore();
const event = ref(null);
const fromPage = ref("index");
const fromDate = ref("");
const showDeleteConfirm = ref(false);
const showEditForm = ref(false);

const { pageActive, pageLeaving, goBack, ANIM_DURATION } = usePageSlideNav({
  getFallbackUrl: () => {
    if (fromPage.value === "day-events" && fromDate.value) {
      return `/pages/day-events/day-events?date=${encodeURIComponent(fromDate.value)}`;
    }
    return "/pages/index/index";
  },
});

const timeRange = computed(() => {
  if (!event.value) return "";
  const start = formatTime(event.value.start_time);
  const end = event.value.end_time ? formatTime(event.value.end_time) : "";
  return end ? `${start} - ${end}` : start;
});

const displayDate = computed(() => {
  if (!event.value) return "";
  return formatDisplayDate(event.value.start_time.slice(0, 10));
});

const repeatLabel = computed(() => {
  if (!event.value) return "";
  return repeatTypeLabel(event.value.repeat_type);
});

onLoad((query) => {
  if (query.id) {
    event.value = calendarStore.getEventById(query.id);
  }
  if (query.from) {
    fromPage.value = query.from;
  }
  if (query.date) {
    fromDate.value = query.date;
  } else if (event.value) {
    fromDate.value = event.value.start_time.slice(0, 10);
  }
});

function onEdit() {
  if (!event.value) return;
  showEditForm.value = true;
}

async function onSaveEdit(data) {
  if (!event.value) return;
  await calendarStore.updateEvent({ id: event.value.id, ...data });
  event.value = calendarStore.getEventById(event.value.id);
  fromDate.value = event.value.start_time.slice(0, 10);
  showEditForm.value = false;
  uni.showToast({ title: "已保存", icon: "success" });
}

function onDelete() {
  showDeleteConfirm.value = true;
}

function confirmDelete() {
  if (event.value) {
    calendarStore.deleteEvent(event.value.id);
    showDeleteConfirm.value = false;
    uni.showToast({ title: "已删除", icon: "success" });
    setTimeout(() => goBack(), 1000);
  }
}
</script>

<style lang="scss" scoped>
@import "./event-detail.scss";
</style>
