/**
 * @typedef {import('./definitions.js').Event} Event
 */

/**
 * 格式化日期为 YYYY-MM-DD
 * @param {Date} date
 * @returns {string}
 */
export function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * 格式化为中文日期显示
 * @param {string} dateStr YYYY-MM-DD
 * @returns {string}
 */
export function formatDisplayDate(dateStr) {
  const [y, m, d] = dateStr.split('-')
  return `${y}年${parseInt(m)}月${parseInt(d)}日`
}

/**
 * 从时间字符串提取 HH:MM
 * @param {string} timeStr
 * @returns {string}
 */
export function formatTime(timeStr) {
  if (!timeStr) return ''
  const part = timeStr.includes(' ') ? timeStr.split(' ')[1] : timeStr
  return part.slice(0, 5)
}

/**
 * 偏移月份
 * @param {number} year
 * @param {number} month 0-11
 * @param {number} delta
 * @returns {{ year: number, month: number }}
 */
export function shiftMonth(year, month, delta) {
  let m = month + delta
  let y = year
  while (m < 0) {
    m += 12
    y -= 1
  }
  while (m > 11) {
    m -= 12
    y += 1
  }
  return { year: y, month: m }
}

/**
 * 获取某月日历网格数据（含前后月补位）
 * @param {number} year
 * @param {number} month 0-11
 * @returns {Array<{date: string, day: number, isCurrentMonth: boolean, isToday: boolean}>}
 */
export function getCalendarDays(year, month) {
  const today = formatDate(new Date())
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startWeekday = firstDay.getDay()

  const days = []

  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    const dateStr = formatDate(d)
    days.push({
      date: dateStr,
      day: d.getDate(),
      isCurrentMonth: false,
      isToday: dateStr === today
    })
  }

  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dateStr = formatDate(new Date(year, month, d))
    days.push({
      date: dateStr,
      day: d,
      isCurrentMonth: true,
      isToday: dateStr === today
    })
  }

  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const d = new Date(year, month + 1, i)
    const dateStr = formatDate(d)
    days.push({
      date: dateStr,
      day: d.getDate(),
      isCurrentMonth: false,
      isToday: dateStr === today
    })
  }

  return days
}

/**
 * 重复类型中文映射
 * @param {string} type
 * @returns {string}
 */
export function repeatTypeLabel(type) {
  const map = {
    none: '不重复',
    daily: '每天',
    weekly: '每周',
    monthly: '每月'
  }
  return map[type] || '不重复'
}

export const WEEKDAY_LABELS = ['日', '一', '二', '三', '四', '五', '六']

const WEEKDAY_CN = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/**
 * 解析 YYYY-MM-DD HH:mm[:ss] 为 Date
 * @param {string} value
 * @returns {Date}
 */
export function parseDateTime(value) {
  if (!value) return new Date()
  const [datePart, timePart = '00:00:00'] = value.split(' ')
  const [y, m, d] = datePart.split('-').map(Number)
  const [hh, mm] = timePart.split(':').map(Number)
  return new Date(y, m - 1, d, hh, mm, 0)
}

/**
 * Date 转为 YYYY-MM-DD HH:mm:00
 * @param {Date} date
 * @returns {string}
 */
export function formatDateTimeValue(date) {
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${formatDate(date)} ${hh}:${mm}:00`
}

/**
 * 滚轮日期列标签，如 5月29日 周五
 * @param {Date} date
 * @returns {string}
 */
export function formatPickerDateLabel(date) {
  const m = date.getMonth() + 1
  const d = date.getDate()
  const wd = WEEKDAY_CN[date.getDay()]
  return `${m}月${d}日 ${wd}`
}

/**
 * 表单行展示：2026年5月29日周五 下午5:30
 * @param {string} value
 * @returns {string}
 */
export function formatDateTimeRow(value) {
  const date = parseDateTime(value)
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const wd = WEEKDAY_CN[date.getDay()]
  const h = date.getHours()
  const min = String(date.getMinutes()).padStart(2, '0')
  const period = h < 12 ? '上午' : '下午'
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
  return `${y}年${m}月${d}日${wd} ${period}${h12}:${min}`
}

/** 全天日程行展示：2026年5月29日周五 */
export function formatDateRow(value) {
  const date = parseDateTime(value)
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const wd = WEEKDAY_CN[date.getDay()]
  return `${y}年${m}月${d}日${wd}`
}

/**
 * 选择器预览：2026年5月29日周五 17:30
 * @param {string} value
 * @returns {string}
 */
export function formatDateTimePreview(value) {
  const date = parseDateTime(value)
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const wd = WEEKDAY_CN[date.getDay()]
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}年${m}月${d}日${wd} ${hh}:${mm}`
}

/**
 * 构建日期滚轮选项
 * @param {Date} center
 * @param {number} beforeDays
 * @param {number} afterDays
 */
export function buildDateWheelOptions(center, beforeDays = 180, afterDays = 730) {
  const options = []
  const base = new Date(center)
  base.setHours(0, 0, 0, 0)
  base.setDate(base.getDate() - beforeDays)

  const total = beforeDays + afterDays + 1
  for (let i = 0; i < total; i++) {
    const d = new Date(base)
    d.setDate(base.getDate() + i)
    options.push({
      value: formatDate(d),
      label: formatPickerDateLabel(d)
    })
  }
  return options
}

/**
 * 选中日期相对今天的偏移文案
 * @param {string} dateStr YYYY-MM-DD
 * @returns {string} 今天 | N天后 | N天前
 */
export function getDaysOffsetLabel(dateStr) {
  if (!dateStr) return ''
  const today = formatDate(new Date())
  if (dateStr === today) return '今天'

  const [sy, sm, sd] = dateStr.split('-').map(Number)
  const [ty, tm, td] = today.split('-').map(Number)
  const selected = Date.UTC(sy, sm - 1, sd)
  const now = Date.UTC(ty, tm - 1, td)
  const diffDays = Math.round((selected - now) / 86400000)

  if (diffDays > 0) return `${diffDays}天后`
  return `${Math.abs(diffDays)}天前`
}

export const MONTH_LABELS = [
  '一月', '二月', '三月', '四月', '五月', '六月',
  '七月', '八月', '九月', '十月', '十一月', '十二月'
]
