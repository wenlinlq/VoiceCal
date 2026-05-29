<template>
  <view v-if="visible" class="form-mask" @tap="onClose">
    <view class="form-dialog" @tap.stop>
      <view class="form-header">
        <text class="form-title">新建日程</text>
        <view class="close-btn" @tap="onClose">
          <text>✕</text>
        </view>
      </view>

      <view class="form-body">
        <view class="form-item">
          <text class="form-label">标题</text>
          <input
            v-model="form.title"
            class="form-input"
            placeholder="请输入日程标题"
            maxlength="50"
          />
        </view>

        <view class="form-item">
          <text class="form-label">日期</text>
          <picker mode="date" :value="form.date" @change="onDateChange">
            <view class="form-picker">{{ form.date || '选择日期' }}</view>
          </picker>
        </view>

        <view class="form-row">
          <view class="form-item half">
            <text class="form-label">开始</text>
            <picker mode="time" :value="form.startTime" @change="onStartChange">
              <view class="form-picker">{{ form.startTime }}</view>
            </picker>
          </view>
          <view class="form-item half">
            <text class="form-label">结束</text>
            <picker mode="time" :value="form.endTime" @change="onEndChange">
              <view class="form-picker">{{ form.endTime }}</view>
            </picker>
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">重复</text>
          <picker :range="repeatOptions" range-key="label" :value="repeatIndex" @change="onRepeatChange">
            <view class="form-picker">{{ repeatOptions[repeatIndex].label }}</view>
          </picker>
        </view>

        <view class="form-item">
          <text class="form-label">备注</text>
          <textarea
            v-model="form.note"
            class="form-textarea"
            placeholder="选填"
            maxlength="200"
            :auto-height="true"
          />
        </view>
      </view>

      <view class="form-actions">
        <view class="btn btn-cancel" @tap="onClose">
          <text>取消</text>
        </view>
        <view class="btn btn-save" @tap="onSave">
          <text>保存</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  defaultDate: { type: String, default: '' }
})

const emit = defineEmits(['close', 'save'])

const repeatOptions = [
  { value: 'none', label: '不重复' },
  { value: 'daily', label: '每天' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' }
]

const form = ref({
  title: '',
  date: '',
  startTime: '09:00',
  endTime: '10:00',
  repeat_type: 'none',
  note: ''
})

const repeatIndex = computed(() => {
  return repeatOptions.findIndex((o) => o.value === form.value.repeat_type)
})

watch(() => props.visible, (val) => {
  if (val) {
    form.value = {
      title: '',
      date: props.defaultDate,
      startTime: '09:00',
      endTime: '10:00',
      repeat_type: 'none',
      note: ''
    }
  }
})

function onDateChange(e) {
  form.value.date = e.detail.value
}

function onStartChange(e) {
  form.value.startTime = e.detail.value
}

function onEndChange(e) {
  form.value.endTime = e.detail.value
}

function onRepeatChange(e) {
  form.value.repeat_type = repeatOptions[e.detail.value].value
}

function onClose() {
  emit('close')
}

function onSave() {
  if (!form.value.title.trim()) {
    uni.showToast({ title: '请输入标题', icon: 'none' })
    return
  }
  if (!form.value.date) {
    uni.showToast({ title: '请选择日期', icon: 'none' })
    return
  }
  emit('save', {
    title: form.value.title.trim(),
    start_time: `${form.value.date} ${form.value.startTime}:00`,
    end_time: `${form.value.date} ${form.value.endTime}:00`,
    repeat_type: form.value.repeat_type,
    note: form.value.note.trim()
  })
}
</script>

<style lang="scss" scoped>
.form-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  z-index: 1000;
}

.form-dialog {
  width: 100%;
  background: #fff;
  border-radius: 32rpx 32rpx 0 0;
  padding: 32rpx 32rpx calc(32rpx + env(safe-area-inset-bottom));
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32rpx;
}

.form-title {
  font-size: 34rpx;
  font-weight: 600;
  color: #1a1a1a;
}

.close-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 28rpx;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 12rpx;

  &.half {
    flex: 1;
  }
}

.form-row {
  display: flex;
  gap: 24rpx;
}

.form-label {
  font-size: 26rpx;
  color: #666;
}

.form-input,
.form-picker,
.form-textarea {
  background: #f5f7fa;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  font-size: 28rpx;
  color: #333;
}

.form-textarea {
  min-height: 120rpx;
}

.form-actions {
  display: flex;
  gap: 24rpx;
  margin-top: 40rpx;
}

.btn {
  flex: 1;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 44rpx;
  font-size: 30rpx;
  font-weight: 500;

  &:active { opacity: 0.85; }
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.btn-save {
  background: #1a73e8;
  color: #fff;
}
</style>
