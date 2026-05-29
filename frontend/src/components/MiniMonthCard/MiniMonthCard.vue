<template>
  <view class="mini-month-card" @tap="$emit('select')">
    <text class="month-title" :class="{ current: isCurrentMonth }">{{ monthIndex + 1 }}月</text>
    <CalendarMonthGrid
      :year="year"
      :month="monthIndex"
      :events="events"
      :current-date="currentDate"
      compact
      :interactive="false"
    />
  </view>
</template>

<script setup>
import CalendarMonthGrid from '@/components/CalendarMonthGrid/CalendarMonthGrid.vue'

defineProps({
  year: { type: Number, required: true },
  monthIndex: { type: Number, required: true },
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: '' },
  isCurrentMonth: { type: Boolean, default: false }
})

defineEmits(['select'])
</script>

<style lang="scss" scoped>
.mini-month-card {
  width: calc((100% - 32rpx) / 3);
  margin-bottom: 24rpx;
  padding: 8rpx 4rpx 12rpx;
  border-radius: 12rpx;

  &:active {
    background: #f5f9ff;
  }
}

.month-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 8rpx;
  padding-left: 4rpx;

  &.current {
    color: #1a73e8;
  }
}
</style>
