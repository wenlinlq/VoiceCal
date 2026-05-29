<template>
  <view class="page-index">
    <view class="top-bar">
      <view class="ws-status" :class="{ connected: wsStore.connected }">
        <view class="status-dot" />
        <text>{{ wsStore.connected ? '已连接' : '未连接' }}</text>
      </view>
      <view class="settings-btn" @tap="goSettings">
        <text>⚙️</text>
      </view>
    </view>

    <VoiceStatus
      v-if="showVoiceStatus"
      :agent-state="agentState"
      :asr-text="voiceStore.displayText"
      :visible="true"
    />

    <CalendarView
      :events="calendarStore.events"
      :current-date="calendarStore.currentDate"
      :view-year="calendarStore.viewYear"
      :view-month="calendarStore.viewMonth"
      :disabled="isInteractionDisabled"
      @date-change="onDateChange"
      @date-click="onDateChange"
      @month-change="onMonthChange"
    />

    <EventList
      :events="calendarStore.todayEvents"
      :current-date="calendarStore.currentDate"
      :disabled="isInteractionDisabled"
      @item-click="onEventClick"
    />

    <view class="mic-area">
      <FloatingMic
        :show="true"
        :status="voiceStore.status"
        :disabled="voiceStore.status === 'processing'"
        @start="onRecordStart"
        @stop="onRecordStop"
      />
    </view>

    <ConfirmDialog
      :visible="confirmStore.visible"
      :message="confirmStore.message"
      :event="confirmStore.event"
      @confirm="onConfirm"
      @cancel="onCancel"
    />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useCalendarStore } from '@/store/modules/calendar.js'
import { useVoiceStore } from '@/store/modules/voice.js'
import { useWebSocketStore } from '@/store/modules/websocket.js'
import { useConfirmStore } from '@/store/modules/confirm.js'
import CalendarView from '@/components/CalendarView/CalendarView.vue'
import EventList from '@/components/EventList/EventList.vue'
import FloatingMic from '@/components/FloatingMic/FloatingMic.vue'
import VoiceStatus from '@/components/VoiceStatus/VoiceStatus.vue'
import ConfirmDialog from '@/components/ConfirmDialog/ConfirmDialog.vue'

const calendarStore = useCalendarStore()
const voiceStore = useVoiceStore()
const wsStore = useWebSocketStore()
const confirmStore = useConfirmStore()

const agentState = ref('listening')

const isInteractionDisabled = computed(() => {
  return voiceStore.status === 'recording' || voiceStore.status === 'processing'
})

const showVoiceStatus = computed(() => {
  return voiceStore.status !== 'idle' || !!voiceStore.displayText
})

function onDateChange(date) {
  calendarStore.setCurrentDate(date)
}

function onMonthChange(year, month) {
  calendarStore.setViewMonth(year, month)
}

function onEventClick(event) {
  uni.navigateTo({
    url: `/pages/event-detail/event-detail?id=${event.id}`
  })
}

function goSettings() {
  uni.navigateTo({ url: '/pages/settings/settings' })
}

function onRecordStart() {
  voiceStore.setStatus('recording')
  agentState.value = 'listening'
  uni.vibrateShort({ type: 'light' })
}

function onRecordStop() {
  voiceStore.setStatus('processing')
  agentState.value = 'thinking'

  // 静态演示：模拟 ASR 识别与处理流程
  setTimeout(() => {
    voiceStore.setAsrText('明天下午3点开会', true)
    agentState.value = 'listening'
  }, 800)

  setTimeout(() => {
    agentState.value = 'speaking'
    voiceStore.setStatus('speaking')
  }, 2000)

  setTimeout(() => {
    voiceStore.reset()
    agentState.value = 'listening'
  }, 3500)
}

function onConfirm() {
  confirmStore.confirm()
}

function onCancel() {
  confirmStore.cancel()
}
</script>

<style lang="scss" scoped>
@import './index.scss';
</style>
