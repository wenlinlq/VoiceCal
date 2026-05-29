<template>
  <!-- #ifdef H5 -->
  <Teleport to="body">
    <div v-if="mounted" class="form-overlay" :class="{ active }">
      <div class="form-mask" @click="onClose" />
      <div class="form-dialog" @click="closeRepeatMenu">
        <div class="form-header">
          <span class="form-title">{{ formTitle }}</span>
          <div class="close-btn" @click="onClose">
            <span>关闭</span>
          </div>
        </div>

        <div class="form-body">
          <div class="form-item">
            <label class="form-label">标题</label>
            <input
              v-model="form.title"
              class="form-input"
              type="text"
              placeholder="请输入日程标题"
              maxlength="50"
            />
          </div>

          <div class="time-list">
            <div class="time-row" @click.stop="openPicker('start')">
              <span class="time-label">开始时间</span>
              <span class="time-value">
                {{ startDisplay }}
                <span class="chevron">›</span>
              </span>
            </div>
            <div class="time-row" @click.stop="openPicker('end')">
              <span class="time-label">结束时间</span>
              <span class="time-value">
                {{ endDisplay }}
                <span class="chevron">›</span>
              </span>
            </div>
          </div>

          <div class="form-item repeat-item">
            <label class="form-label">重复</label>
            <div class="repeat-field" @click.stop>
              <div class="form-picker" @click.stop="toggleRepeatMenu">
                <span>{{ repeatLabel }}</span>
                <span class="picker-arrow">▾</span>
              </div>
              <div v-if="repeatMenuOpen" class="repeat-dropdown">
                <div
                  v-for="opt in repeatOptions"
                  :key="opt.value"
                  class="repeat-option"
                  :class="{ active: form.repeat_type === opt.value }"
                  @click.stop="selectRepeat(opt.value)"
                >
                  {{ opt.label }}
                </div>
              </div>
            </div>
          </div>

          <div class="form-item">
            <label class="form-label">备注</label>
            <textarea
              v-model="form.note"
              class="form-textarea"
              placeholder="选填"
              maxlength="200"
              rows="3"
            />
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-cancel" @click="onClose">取消</button>
          <button type="button" class="btn btn-save" @click="onSave">保存</button>
        </div>
      </div>
    </div>

    <DateTimePicker
      :visible="pickerVisible"
      :title="pickerTitle"
      :model-value="pickerValue"
      @close="pickerVisible = false"
      @confirm="onPickerConfirm"
    />
  </Teleport>
  <!-- #endif -->

  <!-- #ifndef H5 -->
  <view v-if="mounted" class="form-overlay" :class="{ active }">
    <view class="form-mask" @tap="onClose" />

    <view class="form-dialog">
      <view class="form-header">
        <text class="form-title">{{ formTitle }}</text>
        <view class="close-btn" @tap="onClose">
          <text>关闭</text>
        </view>
      </view>

      <view class="form-body">
        <view class="form-item">
          <text class="form-label">标题</text>
          <input
            v-model="form.title"
            class="form-input"
            type="text"
            placeholder="请输入日程标题"
            maxlength="50"
          />
        </view>

        <view class="time-list">
          <view class="time-row" @tap.stop="openPicker('start')">
            <text class="time-label">开始时间</text>
            <view class="time-value">
              <text>{{ startDisplay }}</text>
              <text class="chevron">›</text>
            </view>
          </view>
          <view class="time-row" @tap.stop="openPicker('end')">
            <text class="time-label">结束时间</text>
            <view class="time-value">
              <text>{{ endDisplay }}</text>
              <text class="chevron">›</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">重复</text>
          <picker
            :range="repeatOptions"
            range-key="label"
            :value="repeatIndex"
            @change="onRepeatChange"
          >
            <view class="form-picker">{{ repeatLabel }}</view>
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

    <DateTimePicker
      :visible="pickerVisible"
      :title="pickerTitle"
      :model-value="pickerValue"
      @close="pickerVisible = false"
      @confirm="onPickerConfirm"
    />
  </view>
  <!-- #endif -->
</template>

<script setup>
import { ref, reactive, watch, computed, onBeforeUnmount } from 'vue'
import { rafTwice } from '@/utils/raf.js'
import {
  formatDate,
  formatDateTimeValue,
  formatDateTimeRow,
  parseDateTime
} from '@/utils/date.js'
import DateTimePicker from '@/components/DateTimePicker/DateTimePicker.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  defaultDate: { type: String, default: '' },
  mode: { type: String, default: 'create' },
  eventData: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const repeatOptions = [
  { value: 'none', label: '不重复' },
  { value: 'daily', label: '每天' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' }
]

const form = reactive({
  title: '',
  startDateTime: '',
  endDateTime: '',
  repeat_type: 'none',
  note: ''
})

const ANIM_DURATION = 320

const mounted = ref(false)
const active = ref(false)
const repeatMenuOpen = ref(false)
const pickerVisible = ref(false)
const pickerTarget = ref('start')

let hideTimer = null

const repeatIndex = computed(() => {
  const idx = repeatOptions.findIndex((o) => o.value === form.repeat_type)
  return idx >= 0 ? idx : 0
})

const repeatLabel = computed(() => {
  return repeatOptions[repeatIndex.value]?.label || '不重复'
})

const formTitle = computed(() =>
  props.mode === 'edit' ? '编辑日程' : '新建日程'
)

const startDisplay = computed(() => formatDateTimeRow(form.startDateTime))
const endDisplay = computed(() => formatDateTimeRow(form.endDateTime))

const pickerTitle = computed(() =>
  pickerTarget.value === 'start' ? '开始时间' : '结束时间'
)

const pickerValue = computed(() =>
  pickerTarget.value === 'start' ? form.startDateTime : form.endDateTime
)

watch(
  () => props.visible,
  (val) => {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
    if (val) {
      loadForm()
      mounted.value = true
      rafTwice(() => {
        active.value = true
      })
    } else if (mounted.value) {
      active.value = false
      repeatMenuOpen.value = false
      pickerVisible.value = false
      hideTimer = setTimeout(() => {
        mounted.value = false
      }, ANIM_DURATION)
    }
  }
)

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
})

function buildDefaultStart() {
  const base = props.defaultDate || formatDate(new Date())
  return `${base} 09:00:00`
}

function buildDefaultEnd() {
  const base = props.defaultDate || formatDate(new Date())
  return `${base} 10:00:00`
}

function resetForm() {
  form.title = ''
  form.startDateTime = buildDefaultStart()
  form.endDateTime = buildDefaultEnd()
  form.repeat_type = 'none'
  form.note = ''
}

function loadForm() {
  if (props.mode === 'edit' && props.eventData) {
    form.title = props.eventData.title || ''
    form.startDateTime = props.eventData.start_time || buildDefaultStart()
    form.endDateTime = props.eventData.end_time || buildDefaultEnd()
    form.repeat_type = props.eventData.repeat_type || 'none'
    form.note = props.eventData.note || ''
    return
  }
  resetForm()
}

function onRepeatChange(e) {
  form.repeat_type = repeatOptions[e.detail.value].value
}

function openPicker(target) {
  closeRepeatMenu()
  pickerTarget.value = target
  pickerVisible.value = true
}

function onPickerConfirm(value) {
  if (pickerTarget.value === 'start') {
    form.startDateTime = value
    if (parseDateTime(form.endDateTime) <= parseDateTime(value)) {
      const end = parseDateTime(value)
      end.setHours(end.getHours() + 1)
      form.endDateTime = formatDateTimeValue(end)
    }
  } else {
    form.endDateTime = value
    if (parseDateTime(value) <= parseDateTime(form.startDateTime)) {
      uni.showToast({ title: '结束时间需晚于开始时间', icon: 'none' })
      const end = parseDateTime(form.startDateTime)
      end.setHours(end.getHours() + 1)
      form.endDateTime = formatDateTimeValue(end)
    }
  }
}

function toggleRepeatMenu() {
  repeatMenuOpen.value = !repeatMenuOpen.value
}

function closeRepeatMenu() {
  repeatMenuOpen.value = false
}

function selectRepeat(value) {
  form.repeat_type = value
  repeatMenuOpen.value = false
}

function onClose() {
  emit('close')
}

function onSave() {
  if (!form.title.trim()) {
    uni.showToast({ title: '请输入标题', icon: 'none' })
    return
  }
  emit('save', {
    ...(props.mode === 'edit' && props.eventData ? { id: props.eventData.id } : {}),
    title: form.title.trim(),
    start_time: form.startDateTime,
    end_time: form.endDateTime,
    repeat_type: form.repeat_type,
    note: form.note.trim()
  })
}
</script>

<style lang="scss" scoped>
.form-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.form-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.32s ease;
}

.form-overlay.active .form-mask {
  background-color: rgba(0, 0, 0, 0.45);
}

.form-dialog {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  width: 100%;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  transform: translateY(100%);
  transition: transform 0.32s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.form-overlay.active .form-dialog {
  transform: translateY(0);
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.form-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
}

.close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
  flex-shrink: 0;
  cursor: pointer;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  color: #666;
}

.form-input,
.form-picker,
.form-textarea {
  width: 100%;
  min-height: 44px;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 15px;
  color: #333;
  box-sizing: border-box;
  line-height: 1.4;
}

.form-input,
.form-textarea {
  border: none;
  outline: none;
  font-family: inherit;
}

.form-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.form-textarea {
  min-height: 88px;
  resize: vertical;
}

.time-list {
  display: flex;
  flex-direction: column;
}

.time-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 8px 0;
  cursor: pointer;

  &:not(:last-child) {
    border-bottom: 1px solid #f0f0f0;
  }

  &:active {
    opacity: 0.7;
  }
}

.time-label {
  flex-shrink: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.time-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  font-size: 14px;
  color: #888;
  text-align: right;
}

.chevron {
  color: #ccc;
  font-size: 18px;
  line-height: 1;
  margin-left: 2px;
}

.repeat-item {
  position: relative;
}

.repeat-field {
  position: relative;
}

.picker-arrow {
  font-size: 12px;
  color: #999;
  margin-left: 6px;
}

.repeat-dropdown {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  z-index: 10;
}

.repeat-option {
  padding: 12px 14px;
  font-size: 15px;
  color: #333;
  cursor: pointer;

  &.active {
    color: #1a73e8;
    background: #f5f9ff;
  }

  &:hover {
    background: #f5f5f5;
  }
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn {
  flex: 1;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 22px;
  font-size: 15px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.btn-save {
  background: #1a73e8;
  color: #fff;
}

/* #ifndef H5 */
.form-dialog {
  border-radius: 32rpx 32rpx 0 0;
  padding: 32rpx 32rpx calc(32rpx + env(safe-area-inset-bottom));
}

.form-header {
  margin-bottom: 32rpx;
}

.form-title {
  font-size: 34rpx;
}

.close-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
}

.form-body {
  gap: 24rpx;
}

.form-item {
  gap: 12rpx;
}

.form-label {
  font-size: 26rpx;
}

.form-input,
.form-picker,
.form-textarea {
  min-height: 88rpx;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  font-size: 28rpx;
}

.form-textarea {
  min-height: 120rpx;
}

.time-row {
  min-height: 104rpx;
  padding: 16rpx 0;
  gap: 24rpx;
}

.time-label {
  font-size: 32rpx;
}

.time-value {
  font-size: 28rpx;
  gap: 8rpx;
}

.chevron {
  font-size: 36rpx;
}

.form-actions {
  gap: 24rpx;
  margin-top: 40rpx;
}

.btn {
  height: 88rpx;
  border-radius: 44rpx;
  font-size: 30rpx;
}
/* #endif */
</style>
