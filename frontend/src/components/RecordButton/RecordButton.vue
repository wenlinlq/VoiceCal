<template>
  <view
    class="record-btn"
    :class="[`status-${status}`, `pos-${position}`, { 'in-session': inSession }]"
    @tap.stop="onTap"
  >
    <view v-if="isListening" class="wave-ring ring-1" />
    <view v-if="isListening" class="wave-ring ring-2" />
    <view v-if="isListening" class="wave-ring ring-3" />

    <view class="btn-inner">
      <text class="btn-text">{{ statusText }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  status: {
    type: String,
    default: "idle",
    validator: (v) =>
      ["idle", "recording", "thinking", "speaking", "auto_listening"].includes(v),
  },
  inSession: { type: Boolean, default: false },
  position: { type: String, default: "bottom" },
});

const emit = defineEmits(["tap"]);

const isListening = computed(
  () => props.status === "recording" || props.status === "auto_listening",
);

const statusText = computed(() => {
  if (props.inSession || props.status !== "idle") return "对话中";
  return "点击说话";
});

function onTap() {
  emit("tap");
}
</script>

<style lang="scss" scoped>
@import "./RecordButton.scss";
</style>
