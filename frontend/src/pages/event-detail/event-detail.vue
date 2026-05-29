<template>
  <view class="page-detail">
    <view v-if="event" class="detail-content">
      <view class="title-section">
        <text class="title-icon">📅</text>
        <text class="event-title">{{ event.title }}</text>
      </view>

      <view class="info-card">
        <view class="info-row">
          <text class="info-label">🕐 时间</text>
          <text class="info-value">{{ timeRange }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">📅 日期</text>
          <text class="info-value">{{ displayDate }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">🔁 重复</text>
          <text class="info-value">{{ repeatLabel }}</text>
        </view>
        <view v-if="event.note" class="info-row">
          <text class="info-label">📝 备注</text>
          <text class="info-value">{{ event.note }}</text>
        </view>
      </view>

      <view class="action-bar">
        <view class="action-btn edit-btn" @tap="onEdit">
          <text>编辑</text>
        </view>
        <view class="action-btn delete-btn" @tap="onDelete">
          <text>删除</text>
        </view>
      </view>

      <view class="voice-modify">
        <RecordButton
          status="idle"
          position="bottom"
          @start="onVoiceModify"
        />
        <text class="modify-hint">🎤 修改事件</text>
      </view>
    </view>

    <view v-else class="not-found">
      <text class="not-found-icon">😕</text>
      <text class="not-found-text">事件不存在</text>
      <view class="back-btn" @tap="goBack">
        <text>返回首页</text>
      </view>
    </view>

    <ConfirmDialog
      :visible="showDeleteConfirm"
      :message="'确认删除这个会议吗？'"
      :event="event"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirm = false"
    />
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useCalendarStore } from '@/store/modules/calendar.js'
import { formatTime, formatDisplayDate, repeatTypeLabel } from '@/utils/date.js'
import RecordButton from '@/components/RecordButton/RecordButton.vue'
import ConfirmDialog from '@/components/ConfirmDialog/ConfirmDialog.vue'

const calendarStore = useCalendarStore()
const event = ref(null)
const showDeleteConfirm = ref(false)

const timeRange = computed(() => {
  if (!event.value) return ''
  const start = formatTime(event.value.start_time)
  const end = event.value.end_time ? formatTime(event.value.end_time) : ''
  return end ? `${start} - ${end}` : start
})

const displayDate = computed(() => {
  if (!event.value) return ''
  return formatDisplayDate(event.value.start_time.slice(0, 10))
})

const repeatLabel = computed(() => {
  if (!event.value) return ''
  return repeatTypeLabel(event.value.repeat_type)
})

onLoad((query) => {
  if (query.id) {
    event.value = calendarStore.getEventById(query.id)
  }
})

function onEdit() {
  uni.showToast({ title: '编辑功能开发中', icon: 'none' })
}

function onDelete() {
  showDeleteConfirm.value = true
}

function confirmDelete() {
  if (event.value) {
    calendarStore.deleteEvent(event.value.id)
    showDeleteConfirm.value = false
    uni.showToast({ title: '已删除', icon: 'success' })
    setTimeout(() => goBack(), 1000)
  }
}

function onVoiceModify() {
  uni.showToast({ title: '语音修改功能开发中', icon: 'none' })
}

function goBack() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/index/index' }) })
}
</script>

<style lang="scss" scoped>
.page-detail {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24rpx;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
}

.detail-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.title-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48rpx 0 32rpx;
}

.title-icon {
  font-size: 64rpx;
  margin-bottom: 16rpx;
}

.event-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #333;
  text-align: center;
}

.info-card {
  width: 100%;
  background: #fff;
  border-radius: 24rpx;
  padding: 8rpx 0;
  box-shadow: 0 4rpx 24rpx rgba(102, 126, 234, 0.08);
  margin-bottom: 32rpx;
}

.info-row {
  display: flex;
  align-items: flex-start;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }
}

.info-label {
  font-size: 28rpx;
  color: #999;
  min-width: 160rpx;
}

.info-value {
  flex: 1;
  font-size: 28rpx;
  color: #333;
  font-weight: 500;
}

.action-bar {
  display: flex;
  gap: 24rpx;
  width: 100%;
  margin-bottom: 48rpx;
}

.action-btn {
  flex: 1;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 40rpx;
  font-size: 28rpx;
  font-weight: 500;

  &:active {
    opacity: 0.85;
  }
}

.edit-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.delete-btn {
  background: #fff;
  color: #ff6b6b;
  border: 2rpx solid #ff6b6b;
}

.voice-modify {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 24rpx;
}

.modify-hint {
  font-size: 26rpx;
  color: #999;
  margin-top: 16rpx;
}

.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.not-found-icon {
  font-size: 80rpx;
  margin-bottom: 16rpx;
}

.not-found-text {
  font-size: 30rpx;
  color: #999;
  margin-bottom: 32rpx;
}

.back-btn {
  padding: 16rpx 48rpx;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-radius: 40rpx;
  font-size: 28rpx;
}
</style>
