<template>
  <view class="event-items-list">
    <view v-if="events.length === 0" class="empty-state">
      <text class="empty-text">当日暂无日程</text>
      <text class="empty-hint">长按麦克风添加事件</text>
    </view>

    <view v-else class="list-body">
      <EventSwipeItem
        v-for="event in events"
        :key="event.id"
        :event="event"
        :open="openEventId === event.id"
        :disabled="disabled"
        :show-note="showNote"
        @open="openEventId = event.id"
        @close="onItemClose(event.id)"
        @edit="onEdit(event)"
        @delete="onDelete(event)"
        @toggle="toggleComplete(event)"
        @click="emit('itemClick', $event)"
      />
    </view>

    <ConfirmDialog
      :visible="showDeleteConfirm"
      variant="danger"
      title="删除日程"
      message="确认删除这个日程吗？删除后无法恢复。"
      confirm-text="删除"
      :event="deletingEvent"
      @confirm="confirmDelete"
      @cancel="closeDelete"
    />

    <EventFormModal
      :visible="showEditForm"
      mode="edit"
      :event-data="editingEvent"
      @close="closeEdit"
      @save="saveEdit"
    />
  </view>
</template>

<script setup>
import { ref } from "vue";
import EventSwipeItem from "@/components/EventSwipeItem/EventSwipeItem.vue";
import ConfirmDialog from "@/components/ConfirmDialog/ConfirmDialog.vue";
import EventFormModal from "@/components/EventFormModal/EventFormModal.vue";
import { useEventListModals } from "@/composables/useEventListModals.js";

defineProps({
  events: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  showNote: { type: Boolean, default: false },
});

const emit = defineEmits(["itemClick"]);

const openEventId = ref(null);

const {
  showEditForm,
  showDeleteConfirm,
  editingEvent,
  deletingEvent,
  openEdit,
  openDelete,
  saveEdit,
  confirmDelete,
  closeEdit,
  closeDelete,
  toggleComplete,
} = useEventListModals();

function onItemClose(id) {
  if (openEventId.value === id) {
    openEventId.value = null;
  }
}

function onEdit(event) {
  openEventId.value = null;
  openEdit(event);
}

function onDelete(event) {
  openEventId.value = null;
  openDelete(event);
}
</script>

<style lang="scss" scoped>
.list-body {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48rpx 0;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: 24rpx;
  color: #bbb;
}
</style>
