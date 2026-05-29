/**
 * 节假日标记（休/班）
 * @param {string} dateStr YYYY-MM-DD
 * @returns {{ tag: '休'|'班', type: 'rest'|'work', festival?: string }|null}
 */
const HOLIDAY_MARKS = {
  '2026-01-01': { tag: '休', type: 'rest', festival: '元旦' },
  '2026-01-02': { tag: '休', type: 'rest' },
  '2026-01-03': { tag: '休', type: 'rest' },
  '2026-02-15': { tag: '休', type: 'rest' },
  '2026-02-16': { tag: '休', type: 'rest' },
  '2026-02-17': { tag: '休', type: 'rest' },
  '2026-02-18': { tag: '休', type: 'rest' },
  '2026-02-19': { tag: '休', type: 'rest' },
  '2026-02-20': { tag: '休', type: 'rest' },
  '2026-02-21': { tag: '休', type: 'rest' },
  '2026-02-22': { tag: '休', type: 'rest' },
  '2026-02-23': { tag: '休', type: 'rest' },
  '2026-02-28': { tag: '班', type: 'work' },
  '2026-04-04': { tag: '休', type: 'rest' },
  '2026-04-05': { tag: '休', type: 'rest' },
  '2026-04-06': { tag: '休', type: 'rest' },
  '2026-05-01': { tag: '休', type: 'rest', festival: '劳动节' },
  '2026-05-02': { tag: '休', type: 'rest' },
  '2026-05-03': { tag: '休', type: 'rest' },
  '2026-05-04': { tag: '休', type: 'rest', festival: '青年节' },
  '2026-05-05': { tag: '休', type: 'rest' },
  '2026-05-09': { tag: '班', type: 'work' },
  '2026-06-19': { tag: '休', type: 'rest' },
  '2026-06-20': { tag: '休', type: 'rest' },
  '2026-06-21': { tag: '休', type: 'rest' },
  '2026-09-25': { tag: '休', type: 'rest' },
  '2026-09-26': { tag: '休', type: 'rest' },
  '2026-09-27': { tag: '休', type: 'rest' },
  '2026-10-01': { tag: '休', type: 'rest' },
  '2026-10-02': { tag: '休', type: 'rest' },
  '2026-10-03': { tag: '休', type: 'rest' },
  '2026-10-04': { tag: '休', type: 'rest' },
  '2026-10-05': { tag: '休', type: 'rest' },
  '2026-10-06': { tag: '休', type: 'rest' },
  '2026-10-07': { tag: '休', type: 'rest' },
  '2026-10-10': { tag: '班', type: 'work' }
}

export function getHolidayMark(dateStr) {
  return HOLIDAY_MARKS[dateStr] || null
}
