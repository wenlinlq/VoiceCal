import { ref } from "vue";
import { useCalendarStore } from "@/store/modules/calendar.js";
import {
  prepareEventForSave,
  getRemindSuccessHint,
} from "@/utils/mp-subscribe-message.js";

export function useEventListModals() {
  const calendarStore = useCalendarStore();
  const showEditForm = ref(false);
  const showDeleteConfirm = ref(false);
  const editingEvent = ref(null);
  const deletingEvent = ref(null);

  function openEdit(event) {
    editingEvent.value = event;
    showEditForm.value = true;
  }

  function openDelete(event) {
    deletingEvent.value = event;
    showDeleteConfirm.value = true;
  }

  async function saveEdit(data) {
    if (!editingEvent.value) return;
    try {
      const prepared = await prepareEventForSave(data);
      const updated = await calendarStore.updateEvent({
        id: editingEvent.value.id,
        ...prepared,
      });
      showEditForm.value = false;
      editingEvent.value = null;
      uni.showToast({
        title: `已保存${getRemindSuccessHint(updated)}`,
        icon: "success",
        duration: prepared.remind_enabled ? 2800 : 1500,
      });
    } catch (error) {
      uni.showToast({ title: error.message || "保存失败", icon: "none" });
    }
  }

  async function confirmDelete() {
    if (!deletingEvent.value) return;
    try {
      await calendarStore.deleteEvent(deletingEvent.value.id);
      showDeleteConfirm.value = false;
      deletingEvent.value = null;
      uni.showToast({ title: "已删除", icon: "success" });
    } catch (error) {
      uni.showToast({ title: error.message || "删除失败", icon: "none" });
    }
  }

  function closeEdit() {
    showEditForm.value = false;
    editingEvent.value = null;
  }

  function closeDelete() {
    showDeleteConfirm.value = false;
    deletingEvent.value = null;
  }

  async function toggleComplete(event) {
    try {
      await calendarStore.toggleEventComplete(event.id);
    } catch (error) {
      uni.showToast({
        title: error.message || "更新完成状态失败",
        icon: "none",
      });
    }
  }

  return {
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
  };
}
