import { request } from '@/utils/request.js'

/** GET /api/events */
export function listEvents({ start, end } = {}) {
  return request({
    url: '/events',
    query: { start, end },
  })
}

/** GET /api/events/{event_id} */
export function getEvent(eventId) {
  return request({ url: `/events/${eventId}` })
}

/** POST /api/events */
export function createEvent(payload) {
  return request({
    url: '/events',
    method: 'POST',
    data: payload,
  })
}

/** PUT /api/events/{event_id} */
export function updateEvent(eventId, payload) {
  return request({
    url: `/events/${eventId}`,
    method: 'PUT',
    data: payload,
  })
}

/** DELETE /api/events/{event_id} */
export function deleteEvent(eventId) {
  return request({
    url: `/events/${eventId}`,
    method: 'DELETE',
  })
}
