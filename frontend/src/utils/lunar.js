/**
 * 农历转换（1900-2100）
 * @param {number} year
 * @param {number} month 1-12
 * @param {number} day
 * @returns {{ dayCn: string, monthCn: string, festival: string }}
 */
const LUNAR_DAYS = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
  '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
  '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十']

const LUNAR_MONTHS = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊']

const LUNAR_INFO = [
  0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
  0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
  0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
  0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
  0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
  0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06b60,
  0x0aae4, 0x092e0, 0x0d260, 0x0ea65, 0x0d530, 0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0,
  0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, 0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577,
  0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0, 0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0,
  0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0, 0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0,
  0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4, 0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6,
  0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, 0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50,
  0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160, 0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0,
  0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252, 0x0d520
]

const SOLAR_FESTIVALS = {
  '1-1': '元旦',
  '2-14': '情人节',
  '3-8': '妇女节',
  '5-1': '劳动节',
  '5-4': '青年节',
  '6-1': '儿童节',
  '9-10': '教师节',
  '10-1': '国庆节',
  '12-25': '圣诞节'
}

const LUNAR_FESTIVALS = {
  '1-1': '春节',
  '1-15': '元宵',
  '5-5': '端午',
  '7-7': '七夕',
  '8-15': '中秋',
  '9-9': '重阳',
  '12-30': '除夕'
}

function lunarYearDays(year) {
  let sum = 348
  const info = LUNAR_INFO[year - 1900]
  for (let i = 0x8000; i > 0x8; i >>= 1) {
    sum += info & i ? 1 : 0
  }
  return sum + leapDays(year)
}

function leapMonth(year) {
  return LUNAR_INFO[year - 1900] & 0xf
}

function leapDays(year) {
  if (leapMonth(year)) {
    return LUNAR_INFO[year - 1900] & 0x10000 ? 30 : 29
  }
  return 0
}

function monthDays(year, month) {
  return LUNAR_INFO[year - 1900] & (0x10000 >> month) ? 30 : 29
}

function solar2lunar(year, month, day) {
  const base = new Date(1900, 0, 31)
  let offset = Math.floor((new Date(year, month - 1, day) - base) / 86400000)
  let lunarYear = 1900
  let temp = 0

  for (; lunarYear < 2101 && offset > 0; lunarYear++) {
    temp = lunarYearDays(lunarYear)
    offset -= temp
  }
  if (offset < 0) {
    offset += temp
    lunarYear--
  }

  const leap = leapMonth(lunarYear)
  let isLeap = false
  let lunarMonth = 1

  for (; lunarMonth < 13 && offset > 0; lunarMonth++) {
    if (leap > 0 && lunarMonth === leap + 1 && !isLeap) {
      lunarMonth--
      isLeap = true
      temp = leapDays(lunarYear)
    } else {
      temp = monthDays(lunarYear, lunarMonth)
    }
    if (isLeap && lunarMonth === leap + 1) isLeap = false
    offset -= temp
  }

  if (offset === 0 && leap > 0 && lunarMonth === leap + 1) {
    if (isLeap) {
      isLeap = false
    } else {
      isLeap = true
      lunarMonth--
    }
  }
  if (offset < 0) {
    offset += temp
    lunarMonth--
  }

  const lunarDay = offset + 1
  const festivalKey = `${lunarMonth}-${lunarDay}`
  const solarKey = `${month}-${day}`
  const festival = LUNAR_FESTIVALS[festivalKey] || SOLAR_FESTIVALS[solarKey] || ''

  return {
    dayCn: LUNAR_DAYS[lunarDay - 1] || '',
    monthCn: LUNAR_MONTHS[lunarMonth - 1] || '',
    festival
  }
}

/**
 * 获取日期下方副文本（节日优先，否则农历日）
 */
export function getLunarLabel(year, month, day) {
  const lunar = solar2lunar(year, month, day)
  return lunar.festival || lunar.dayCn
}

export { solar2lunar }
