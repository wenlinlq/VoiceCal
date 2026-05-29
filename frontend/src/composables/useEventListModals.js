import { ref } from "vue";
import { useCalendarStore } from "@/store/modules/calendar.js";

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
    await calendarStore.updateEvent({ id: editingEvent.value.id, ...data });
    showEditForm.value = false;
    editingEvent.value = null;
    uni.showToast({ title: "已保存", icon: "success" });
  }

  async function confirmDelete() {
    if (!deletingEvent.value) return;
    await calendarStore.deleteEvent(deletingEvent.value.id);
    showDeleteConfirm.value = false;
    deletingEvent.value = null;
    uni.showToast({ title: "已删除", icon: "success" });
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
    await calendarStore.toggleEventComplete(event.id);
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
