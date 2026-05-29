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
 * 获取某月日历网格数据（含前后月补位）
 * @param {number} year
 * @param {number} month 0-11
 * @returns {Array<{date: string, day: number, isCurrentMonth: boolean, isToday: boolean}>}
 */
export function getCalendarDays(year, month) {
  const today = formatDate(new Date())
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startWeekday = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1

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

export const WEEKDAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']
