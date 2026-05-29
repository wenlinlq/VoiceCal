<template>
  <view class="calendar-view" :class="{ disabled }">
    <view class="calendar-header">
      <view class="nav-btn" @tap="prevMonth">
        <text class="nav-icon">‹</text>
      </view>
      <text class="month-title">{{ monthTitle }}</text>
      <view class="nav-btn" @tap="nextMonth">
        <text class="nav-icon">›</text>
      </view>
    </view>

    <view class="weekday-row">
      <text v-for="label in weekdayLabels" :key="label" class="weekday-cell">{{ label }}</text>
    </view>

    <view class="days-grid">
      <view
        v-for="day in calendarDays"
        :key="day.date"
        class="day-cell"
        :class="{
          'other-month': !day.isCurrentMonth,
          today: day.isToday,
          selected: day.date === currentDate,
          'has-event': hasEvent(day.date)
        }"
        @tap="onDayClick(day)"
      >
        <text class="day-num">{{ day.day }}</text>
        <view v-if="hasEvent(day.date)" class="event-dot" />
      </view>
    </view>

    <view v-if="!hasMonthEvents" class="empty-hint">
      <text>本月暂无日程</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { getCalendarDays, WEEKDAY_LABELS } from '@/utils/date.js'

const props = defineProps({
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: '' },
  viewYear: { type: Number, required: true },
  viewMonth: { type: Number, required: true },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['dateChange', 'dateClick', 'monthChange'])

const weekdayLabels = WEEKDAY_LABELS

const monthTitle = computed(() => `${props.viewYear}年${props.viewMonth + 1}月`)

const calendarDays = computed(() => getCalendarDays(props.viewYear, props.viewMonth))

const eventDateSet = computed(() => {
  const set = new Set()
  props.events.forEach((e) => set.add(e.start_time.slice(0, 10)))
  return set
})

const hasMonthEvents = computed(() => {
  const prefix = `${props.viewYear}-${String(props.viewMonth + 1).padStart(2, '0')}`
  return props.events.some((e) => e.start_time.startsWith(prefix))
})

function hasEvent(dateStr) {
  return eventDateSet.value.has(dateStr)
}

function onDayClick(day) {
  if (props.disabled) return
  emit('dateClick', day.date)
  emit('dateChange', day.date)
}

function prevMonth() {
  if (props.disabled) return
  let y = props.viewYear
  let m = props.viewMonth - 1
  if (m < 0) {
    m = 11
    y -= 1
  }
  emit('monthChange', y, m)
}

function nextMonth() {
  if (props.disabled) return
  let y = props.viewYear
  let m = props.viewMonth + 1
  if (m > 11) {
    m = 0
    y += 1
  }
  emit('monthChange', y, m)
}
</script>

<style lang="scss" scoped>
@import './CalendarView.scss';
</style>
