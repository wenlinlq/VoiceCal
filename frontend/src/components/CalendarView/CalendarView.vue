<template>
  <view
    class="calendar-view"
    :class="{ disabled }"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <!-- 顶部操作栏 -->
    <view class="toolbar">
      <view class="toolbar-actions">
        <view class="icon-btn" @tap.stop="emit('add')">
          <view class="icon-plus" />
        </view>
        <view class="icon-btn" @tap.stop="emit('today')">
          <view class="icon-calendar">
            <view class="cal-dot" />
          </view>
        </view>
        <view class="icon-btn" @tap.stop="emit('menu')">
          <view class="icon-more">
            <view class="dot" />
            <view class="dot" />
            <view class="dot" />
          </view>
        </view>
      </view>
    </view>

    <!-- 年月标题 -->
    <view class="month-row">
      <text class="month-title">{{ viewYear }} / {{ viewMonth + 1 }}</text>
    </view>

    <!-- 星期行 -->
    <view class="weekday-row">
      <text v-for="label in weekdayLabels" :key="label" class="weekday-cell">{{ label }}</text>
    </view>

    <!-- 日期网格 -->
    <view class="days-grid">
      <view
        v-for="day in enrichedDays"
        :key="day.date"
        class="day-cell"
        :class="{
          'other-month': !day.isCurrentMonth,
          selected: day.date === currentDate,
          rest: day.mark?.type === 'rest' && day.date !== currentDate,
          work: day.mark?.type === 'work' && day.date !== currentDate
        }"
        @tap="onDayClick(day)"
      >
        <view v-if="day.mark?.tag" class="day-tag" :class="day.mark.type">
          <text>{{ day.mark.tag }}</text>
        </view>
        <view v-if="day.hasEvent" class="event-dot" />
        <text class="day-num">{{ day.day }}</text>
        <text class="day-sub" :class="{ 'sub-white': day.date === currentDate }">{{ day.subLabel }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getCalendarDays, WEEKDAY_LABELS } from '@/utils/date.js'
import { getLunarLabel } from '@/utils/lunar.js'
import { getHolidayMark } from '@/utils/holidays.js'

const props = defineProps({
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: '' },
  viewYear: { type: Number, required: true },
  viewMonth: { type: Number, required: true },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['dateChange', 'dateClick', 'monthChange', 'add', 'today', 'menu'])

const weekdayLabels = WEEKDAY_LABELS
const touchStartX = ref(0)

const calendarDays = computed(() => getCalendarDays(props.viewYear, props.viewMonth))

const eventDateSet = computed(() => {
  const set = new Set()
  props.events.forEach((e) => set.add(e.start_time.slice(0, 10)))
  return set
})

const enrichedDays = computed(() => {
  return calendarDays.value.map((day) => {
    const [y, m, d] = day.date.split('-').map(Number)
    const mark = getHolidayMark(day.date)
    const lunarLabel = getLunarLabel(y, m, d)
    const subLabel = mark?.festival || lunarLabel
    return {
      ...day,
      mark,
      subLabel,
      hasEvent: eventDateSet.value.has(day.date)
    }
  })
})

function hasEvent(dateStr) {
  return eventDateSet.value.has(dateStr)
}

function onDayClick(day) {
  if (props.disabled) return
  emit('dateClick', day.date)
  emit('dateChange', day.date)
}

function changeMonth(delta) {
  if (props.disabled) return
  let y = props.viewYear
  let m = props.viewMonth + delta
  if (m < 0) { m = 11; y -= 1 }
  if (m > 11) { m = 0; y += 1 }
  emit('monthChange', y, m)
}

function onTouchStart(e) {
  touchStartX.value = e.changedTouches[0].clientX
}

function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientX - touchStartX.value
  if (Math.abs(diff) < 60) return
  changeMonth(diff < 0 ? 1 : -1)
}
</script>

<style lang="scss" scoped>
@import './CalendarView.scss';
</style>
