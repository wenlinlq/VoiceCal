<template>
  <!-- #ifdef H5 -->
  <Teleport to="body">
    <div v-if="mounted" class="form-overlay" :class="{ active }">
      <div class="form-mask" @click="onClose" />
      <div class="form-dialog" @click="closeMenus">
        <div class="form-header">
          <span class="form-title">{{ formTitle }}</span>
          <div class="close-btn" @click="onClose">
            <span>关闭</span>
          </div>
        </div>

        <div class="form-body-wrap">
          <div class="form-body-scroll">
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
            <div class="time-row all-day-row">
              <span class="time-label">全天日程</span>
              <switch
                :checked="form.is_all_day"
                color="#1a73e8"
                @change="onAllDayChange"
              />
            </div>
            <div class="time-row" @click.stop="openPicker('start')">
              <span class="time-label">{{ startTimeLabel }}</span>
              <span class="time-value">
                {{ startDisplay }}
                <span class="chevron">›</span>
              </span>
            </div>
            <div class="time-row" @click.stop="openPicker('end')">
              <span class="time-label">{{ endTimeLabel }}</span>
              <span class="time-value">
                {{ endDisplay }}
                <span class="chevron">›</span>
              </span>
            </div>
          </div>

          <div class="time-row all-day-row">
            <span class="time-label">日程提醒</span>
            <switch
              :checked="form.remind_enabled"
              color="#1a73e8"
              @change="onRemindChange"
            />
          </div>
          <div v-if="form.remind_enabled" class="form-item remind-item">
            <label class="form-label">提前提醒</label>
            <div class="repeat-field" @click.stop>
              <div class="form-picker" @click.stop="toggleRemindMenu">
                <span>{{ remindBeforeLabel }}</span>
                <span class="picker-arrow">▾</span>
              </div>
              <div v-if="remindMenuOpen" class="repeat-dropdown">
                <div
                  v-for="opt in remindBeforeOptions"
                  :key="opt.value"
                  class="repeat-option"
                  :class="{ active: form.remind_before_minutes === opt.value }"
                  @click.stop="selectRemindBefore(opt.value)"
                >
                  {{ opt.label }}
                </div>
              </div>
            </div>
          </div>
          <p v-if="form.remind_enabled" class="remind-hint">保存时将请求微信订阅消息授权</p>

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
      :date-only="form.is_all_day"
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

      <view class="form-body-wrap">
        <scroll-view
          scroll-y
          enhanced
          :show-scrollbar="false"
          :bounces="false"
          class="form-body-scroll"
        >
        <view class="form-scroll-content">
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
          <view class="time-row all-day-row">
            <text class="time-label">全天日程</text>
            <switch
              :checked="form.is_all_day"
              color="#1a73e8"
              @change="onAllDayChange"
            />
          </view>
          <view class="time-row" @tap.stop="openPicker('start')">
            <text class="time-label">{{ startTimeLabel }}</text>
            <view class="time-value">
              <text>{{ startDisplay }}</text>
              <text class="chevron">›</text>
            </view>
          </view>
          <view class="time-row" @tap.stop="openPicker('end')">
            <text class="time-label">{{ endTimeLabel }}</text>
            <view class="time-value">
              <text>{{ endDisplay }}</text>
              <text class="chevron">›</text>
            </view>
          </view>
        </view>

        <view class="time-row all-day-row">
          <text class="time-label">日程提醒</text>
          <switch
            :checked="form.remind_enabled"
            color="#1a73e8"
            @change="onRemindChange"
          />
        </view>
        <view v-if="form.remind_enabled" class="form-item">
          <text class="form-label">提前提醒</text>
          <picker
            :range="remindBeforeOptions"
            range-key="label"
            :value="remindBeforeIndex"
            @change="onRemindBeforeChange"
          >
            <view class="form-picker">{{ remindBeforeLabel }}</view>
          </picker>
        </view>
        <text v-if="form.remind_enabled" class="remind-hint">保存时将请求微信订阅消息授权</text>

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
        </scroll-view>
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
      :date-only="form.is_all_day"
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
  formatDateRow,
  parseDateTime
} from '@/utils/date.js'
import DateTimePicker from '@/components/DateTimePicker/DateTimePicker.vue'
import {
  REMIND_BEFORE_OPTIONS,
  DEFAULT_REMIND_BEFORE_MINUTES,
  computeRemindAt,
  inferRemindBeforeMinutes,
  getRemindBeforeLabel,
} from '@/utils/remind-options.js'

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
  is_all_day: false,
  repeat_type: 'none',
  note: '',
  remind_enabled: false,
  remind_before_minutes: DEFAULT_REMIND_BEFORE_MINUTES,
})

const ANIM_DURATION = 320

const mounted = ref(false)
const active = ref(false)
const repeatMenuOpen = ref(false)
const remindMenuOpen = ref(false)
const remindBeforeOptions = REMIND_BEFORE_OPTIONS
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

const remindBeforeIndex = computed(() => {
  const idx = remindBeforeOptions.findIndex(
    (o) => o.value === form.remind_before_minutes,
  )
  if (idx >= 0) return idx
  const defaultIdx = remindBeforeOptions.findIndex(
    (o) => o.value === DEFAULT_REMIND_BEFORE_MINUTES,
  )
  return defaultIdx >= 0 ? defaultIdx : 0
})

const remindBeforeLabel = computed(() =>
  getRemindBeforeLabel(form.remind_before_minutes),
)

const formTitle = computed(() =>
  props.mode === 'edit' ? '编辑日程' : '新建日程'
)

const startTimeLabel = computed(() =>
  form.is_all_day ? '开始日期' : '开始时间'
)
const endTimeLabel = computed(() =>
  form.is_all_day ? '结束日期' : '结束时间'
)

const startDisplay = computed(() =>
  form.is_all_day
    ? formatDateRow(form.startDateTime)
    : formatDateTimeRow(form.startDateTime)
)
const endDisplay = computed(() =>
  form.is_all_day
    ? formatDateRow(form.endDateTime)
    : formatDateTimeRow(form.endDateTime)
)

const pickerTitle = computed(() =>
  pickerTarget.value === 'start' ? startTimeLabel.value : endTimeLabel.value
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
      remindMenuOpen.value = false
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
  form.is_all_day = false
  form.repeat_type = 'none'
  form.note = ''
  form.remind_enabled = false
  form.remind_before_minutes = DEFAULT_REMIND_BEFORE_MINUTES
}

function loadForm() {
  if (props.mode === 'edit' && props.eventData) {
    form.title = props.eventData.title || ''
    form.startDateTime = props.eventData.start_time || buildDefaultStart()
    form.endDateTime = props.eventData.end_time || buildDefaultEnd()
    form.is_all_day = Boolean(props.eventData.is_all_day)
    form.repeat_type = props.eventData.repeat_type || 'none'
    form.note = props.eventData.note || ''
    form.remind_enabled = Boolean(props.eventData.remind_enabled)
    if (form.remind_enabled && props.eventData.remind_at) {
      form.remind_before_minutes = inferRemindBeforeMinutes(
        form.startDateTime,
        props.eventData.remind_at,
      )
    } else {
      form.remind_before_minutes = DEFAULT_REMIND_BEFORE_MINUTES
    }
    if (form.is_all_day) {
      applyAllDayTimes()
    }
    return
  }
  resetForm()
}

function applyAllDayTimes() {
  const startDate = formatDate(parseDateTime(form.startDateTime))
  let endDate = formatDate(parseDateTime(form.endDateTime))
  if (parseDateTime(form.endDateTime) < parseDateTime(form.startDateTime)) {
    endDate = startDate
  }
  form.startDateTime = `${startDate} 00:00:00`
  form.endDateTime = `${endDate} 23:59:59`
}

function restoreTimedDefaults() {
  const startDate = formatDate(parseDateTime(form.startDateTime))
  const endDate = formatDate(parseDateTime(form.endDateTime))
  form.startDateTime = `${startDate} 09:00:00`
  const endCandidate = parseDateTime(`${endDate} 10:00:00`)
  if (endCandidate <= parseDateTime(form.startDateTime)) {
    const end = parseDateTime(form.startDateTime)
    end.setHours(end.getHours() + 1)
    form.endDateTime = formatDateTimeValue(end)
  } else {
    form.endDateTime = `${endDate} 10:00:00`
  }
}

function onRemindChange(e) {
  const checked =
    e?.detail?.value !== undefined ? Boolean(e.detail.value) : !form.remind_enabled
  form.remind_enabled = checked
}

function onAllDayChange(e) {
  const checked = e?.detail?.value !== undefined
    ? Boolean(e.detail.value)
    : !form.is_all_day
  form.is_all_day = checked
  if (checked) {
    applyAllDayTimes()
  } else {
    restoreTimedDefaults()
  }
}

function onRepeatChange(e) {
  form.repeat_type = repeatOptions[e.detail.value].value
}

function toggleRemindMenu() {
  remindMenuOpen.value = !remindMenuOpen.value
  repeatMenuOpen.value = false
}

function closeRemindMenu() {
  remindMenuOpen.value = false
}

function selectRemindBefore(value) {
  form.remind_before_minutes = value
  remindMenuOpen.value = false
}

function onRemindBeforeChange(e) {
  const opt = remindBeforeOptions[e.detail.value]
  if (opt) form.remind_before_minutes = opt.value
}

function openPicker(target) {
  closeRepeatMenu()
  closeRemindMenu()
  pickerTarget.value = target
  pickerVisible.value = true
}

function onPickerConfirm(value) {
  if (form.is_all_day) {
    const dateStr = formatDate(parseDateTime(value))
    if (pickerTarget.value === 'start') {
      form.startDateTime = `${dateStr} 00:00:00`
      const endDate = formatDate(parseDateTime(form.endDateTime))
      if (parseDateTime(form.endDateTime) < parseDateTime(form.startDateTime)) {
        form.endDateTime = `${dateStr} 23:59:59`
      } else {
        form.endDateTime = `${endDate} 23:59:59`
      }
    } else {
      if (parseDateTime(`${dateStr} 23:59:59`) < parseDateTime(form.startDateTime)) {
        uni.showToast({ title: '结束日期不能早于开始日期', icon: 'none' })
        const startDate = formatDate(parseDateTime(form.startDateTime))
        form.endDateTime = `${startDate} 23:59:59`
      } else {
        form.endDateTime = `${dateStr} 23:59:59`
      }
    }
    return
  }

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
  remindMenuOpen.value = false
}

function closeRepeatMenu() {
  repeatMenuOpen.value = false
}

function closeMenus() {
  closeRepeatMenu()
  closeRemindMenu()
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
  if (form.is_all_day) {
    applyAllDayTimes()
  }
  if (form.remind_enabled) {
    const remindAt = computeRemindAt(
      form.startDateTime,
      form.remind_before_minutes,
    )
    if (parseDateTime(remindAt) >= parseDateTime(form.startDateTime)) {
      uni.showToast({ title: '提醒时间需早于日程开始', icon: 'none' })
      return
    }
  }
  emit('save', {
    ...(props.mode === 'edit' && props.eventData ? { id: props.eventData.id } : {}),
    title: form.title.trim(),
    start_time: form.startDateTime,
    end_time: form.endDateTime,
    is_all_day: form.is_all_day,
    repeat_type: form.repeat_type,
    note: form.note.trim(),
    remind_enabled: form.remind_enabled,
    remind_before_minutes: form.remind_enabled
      ? form.remind_before_minutes
      : undefined,
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
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 75vh;
  max-height: 75vh;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 16px 16px 0;
  box-sizing: border-box;
  overflow: hidden;
  transform: translateY(100%);
  transition: transform 0.32s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.form-overlay.active .form-dialog {
  transform: translateY(0);
}

.form-header {
  display: flex;
  flex-shrink: 0;
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

.form-body-wrap {
  flex: 1;
  min-height: 0;
  height: 0;
  overflow: hidden;
}

.form-body-scroll {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none !important;
  -ms-overflow-style: none !important;

  &::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    background: transparent !important;
  }
}

.form-body-scroll .form-scroll-content,
.form-body-scroll {
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

.all-day-row {
  cursor: default;

  &:active {
    opacity: 1;
  }
}

.remind-hint {
  display: block;
  font-size: 12px;
  color: #888;
  line-height: 1.5;
  margin: -4px 0 4px;
  padding: 0 2px;
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
  flex-shrink: 0;
  gap: 12px;
  margin-top: 16px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom));
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
  height: 75vh;
  max-height: 75vh;
  border-radius: 32rpx 32rpx 0 0;
  padding: 32rpx 32rpx 0;
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

.form-body-wrap {
  flex: 1;
  min-height: 0;
  height: 0;
  overflow: hidden;
}

.form-body-scroll {
  height: 100%;
}

.form-scroll-content {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding-bottom: 8rpx;
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
  margin-top: 24rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
}

.btn {
  height: 88rpx;
  border-radius: 44rpx;
  font-size: 30rpx;
}
/* #endif */
</style>
