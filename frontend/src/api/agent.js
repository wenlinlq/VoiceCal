import { request } from '@/utils/request.js'
import { DEFAULT_USER_ID } from '@/config/api.js'

/**
 * POST /api/agent/text
 * @returns {Promise<{session_id:string,user_id:string,reply_text:string,intent:string}>}
 */
export function sendAgentText({ sessionId, userId = DEFAULT_USER_ID, text }) {
  return request({
    url: '/agent/text',
    method: 'POST',
    data: {
      session_id: sessionId,
      user_id: userId,
      text,
    },
    raw: true,
  })
}
