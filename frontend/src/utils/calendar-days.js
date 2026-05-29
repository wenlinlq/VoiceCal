import { getCalendarDays } from '@/utils/date.js'
import { getLunarLabel, getLunarLineType } from '@/utils/lunar.js'
import { getHolidayMark } from '@/utils/holidays.js'

/**
 * 构建带农历、节假日、日程标记的日期列表
 * @param {number} year
 * @param {number} month
 * @param {string[]} eventList 事件列表（含 start_time）
 * @param {string} currentDate YYYY-MM-DD
 */
export function buildEnrichedDays(year, month, eventList = [], currentDate = '') {
  const eventDates = new Set(eventList.map((e) => e.start_time.slice(0, 10)))

  return getCalendarDays(year, month).map((day) => {
    const [y, m, d] = day.date.split('-').map(Number)
    const mark = getHolidayMark(day.date)
    const subLabel = mark?.festival || getLunarLabel(y, m, d)
    const lunarLine = getLunarLineType(y, m, d)

    return {
      ...day,
      mark,
      subLabel,
      lunarLine,
      hasEvent: eventDates.has(day.date),
      selected: day.date === currentDate
    }
  })
}
