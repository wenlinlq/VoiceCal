<template>
  <view class="month-grid" :class="{ compact, interactive }">
    <view v-if="showWeekday" class="weekday-row">
      <text v-for="label in weekdayLabels" :key="label" class="weekday-cell">{{ label }}</text>
    </view>

    <view class="days-grid">
      <view
        v-for="day in days"
        :key="day.date"
        class="day-cell"
        :class="{
          'other-month': !day.isCurrentMonth,
          selected: day.selected,
          rest: day.mark?.type === 'rest' && !day.selected,
          work: day.mark?.type === 'work' && !day.selected,
          'has-event': day.hasEvent
        }"
        @tap="onDayTap(day)"
      >
        <view v-if="!compact && day.mark?.tag" class="day-tag" :class="day.mark.type">
          <text>{{ day.mark.tag }}</text>
        </view>
        <view v-if="!compact && day.hasEvent" class="event-dot" />
        <text class="day-num">{{ day.day }}</text>
        <view
          v-if="compact && day.lunarLine"
          class="lunar-line"
          :class="day.lunarLine"
        />
        <text
          v-if="!compact"
          class="day-sub"
          :class="{ 'sub-white': day.selected }"
        >{{ day.subLabel }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { WEEKDAY_LABELS } from '@/utils/date.js'
import { buildEnrichedDays } from '@/utils/calendar-days.js'

const props = defineProps({
  year: { type: Number, required: true },
  month: { type: Number, required: true },
  events: { type: Array, default: () => [] },
  currentDate: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  showWeekday: { type: Boolean, default: true },
  interactive: { type: Boolean, default: true }
})

const emit = defineEmits(['dayClick'])

const weekdayLabels = WEEKDAY_LABELS

const days = computed(() =>
  buildEnrichedDays(props.year, props.month, props.events, props.currentDate)
)

function onDayTap(day) {
  if (!props.interactive) return
  emit('dayClick', day)
}
</script>

<style lang="scss" scoped>
.month-grid {
  width: 100%;
}

.weekday-row {
  display: flex;
  margin-bottom: 8rpx;
}

.weekday-cell {
  flex: 1;
  text-align: center;
  font-size: 26rpx;
  color: #999;
}

.month-grid.compact .weekday-cell {
  font-size: 18rpx;
  margin-bottom: 0;
}

.month-grid.compact .weekday-row {
  margin-bottom: 4rpx;
}

.days-grid {
  display: flex;
  flex-wrap: wrap;
}

.month-grid:not(.compact) .day-cell {
  min-height: 108rpx;
  padding: 8rpx 4rpx;
  margin-bottom: 4rpx;
  border-radius: 16rpx;
}

.month-grid.compact .day-cell {
  min-height: 44rpx;
  padding: 2rpx 0;
}

.day-cell {
  width: calc(100% / 7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  border-radius: 12rpx;

  &.other-month .day-num {
    color: #ccc;
  }

  &.rest {
    background: #e8f4fd;
  }

  &.work {
    background: #f0f0f0;
  }

  &.selected {
    background: #1a73e8;

    .day-num,
    .day-sub {
      color: #fff;
      font-weight: 600;
    }

    .event-dot {
      background: #fff;
    }
  }
}

.day-tag {
  position: absolute;
  top: 2rpx;
  right: 4rpx;
  font-size: 16rpx;
  padding: 0 4rpx;
  border-radius: 4rpx;

  &.rest {
    color: #1a73e8;
    background: rgba(26, 115, 232, 0.12);
  }

  &.work {
    color: #e53935;
    background: rgba(229, 57, 53, 0.1);
  }
}

.event-dot {
  width: 8rpx;
  height: 8rpx;
  border-radius: 50%;
  background: #999;
  margin-bottom: 2rpx;

  .selected & {
    background: #fff;
  }
}

.day-num {
  font-size: 32rpx;
  color: #333;
  line-height: 1.2;
  font-weight: 500;
}

.month-grid.compact .day-num {
  font-size: 22rpx;
  line-height: 1;
}

.lunar-line {
  width: 20rpx;
  height: 4rpx;
  border-radius: 2rpx;
  margin-top: 2rpx;

  &.red {
    background: #e53935;
  }

  &.blue {
    background: #1a73e8;
  }
}

.day-sub {
  font-size: 20rpx;
  color: #999;
  margin-top: 4rpx;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;

  &.sub-white {
    color: rgba(255, 255, 255, 0.85);
  }
}
</style>
