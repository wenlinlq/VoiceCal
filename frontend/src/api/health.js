import { request } from '@/utils/request.js'

/** GET /api/health */
export function checkHealth() {
  return request({ url: '/health' })
}
