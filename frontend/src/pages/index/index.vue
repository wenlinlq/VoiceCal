<template>
  <view class="page-index">
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
      @add="openCreateForm"
      @today="goToday"
      @menu="onMenu"
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

    <EventFormModal
      :visible="showCreateForm"
      :default-date="calendarStore.currentDate"
      @close="showCreateForm = false"
      @save="onCreateEvent"
    />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatDate } from '@/utils/date.js'
import { useCalendarStore } from '@/store/modules/calendar.js'
import { useVoiceStore } from '@/store/modules/voice.js'
import { useConfirmStore } from '@/store/modules/confirm.js'
import CalendarView from '@/components/CalendarView/CalendarView.vue'
import EventList from '@/components/EventList/EventList.vue'
import FloatingMic from '@/components/FloatingMic/FloatingMic.vue'
import VoiceStatus from '@/components/VoiceStatus/VoiceStatus.vue'
import ConfirmDialog from '@/components/ConfirmDialog/ConfirmDialog.vue'
import EventFormModal from '@/components/EventFormModal/EventFormModal.vue'

const calendarStore = useCalendarStore()
const voiceStore = useVoiceStore()
const confirmStore = useConfirmStore()

const agentState = ref('listening')
const showCreateForm = ref(false)

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

function openCreateForm() {
  showCreateForm.value = true
}

function goToday() {
  const today = formatDate(new Date())
  const now = new Date()
  calendarStore.setCurrentDate(today)
  calendarStore.setViewMonth(now.getFullYear(), now.getMonth())
}

function onMenu() {
  uni.showActionSheet({
    itemList: ['设置', '使用引导'],
    success: (res) => {
      if (res.tapIndex === 0) {
        uni.navigateTo({ url: '/pages/settings/settings' })
      } else if (res.tapIndex === 1) {
        uni.showModal({
          title: '语音指令示例',
          content: '「明天下午3点开会」— 添加日程\n「今天有什么安排」— 查看今日事件\n「删除今天下午3点的会」— 删除事件',
          showCancel: false
        })
      }
    }
  })
}

async function onCreateEvent(data) {
  await calendarStore.addEvent(data)
  showCreateForm.value = false
  calendarStore.setCurrentDate(data.start_time.slice(0, 10))
  uni.showToast({ title: '日程已创建', icon: 'success' })
}

function onRecordStart() {
  voiceStore.setStatus('recording')
  agentState.value = 'listening'
  uni.vibrateShort({ type: 'light' })
}

function onRecordStop() {
  voiceStore.setStatus('processing')
  agentState.value = 'thinking'

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
