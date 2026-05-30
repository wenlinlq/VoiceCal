/** 前端时间 "YYYY-MM-DD HH:mm:ss" → API ISO 8601 */
export function toApiDateTime(str) {
  if (!str) return str
  if (str.includes('T')) return str
  return `${str.replace(' ', 'T')}+08:00`
}

/** API 时间 → 前端 "YYYY-MM-DD HH:mm:ss" */
export function fromApiDateTime(str) {
  if (!str) return ''
  return String(str).replace('T', ' ').replace(/(\.\d+)?(Z|[+-]\d{2}:\d{2})$/, '').slice(0, 19)
}

/** 后端 EventResponse → 前端 Event */
export function normalizeEvent(raw) {
  return {
    id: raw.id,
    title: raw.title,
    start_time: fromApiDateTime(raw.start_time),
    end_time: fromApiDateTime(raw.end_time),
    note: raw.description || '',
    location: raw.location || '',
    is_all_day: Boolean(raw.is_all_day),
    repeat_type: 'none',
    completed: false,
  }
}

/** 前端表单 → 后端 EventCreate / EventUpdate */
export function toApiEventPayload(event) {
  const payload = {
    title: event.title,
    description: event.note || null,
    location: event.location || null,
    start_time: toApiDateTime(event.start_time),
    end_time: toApiDateTime(event.end_time),
    is_all_day: Boolean(event.is_all_day),
  }

  if (event.title === undefined) delete payload.title
  if (event.note === undefined) delete payload.description

  return payload
}
