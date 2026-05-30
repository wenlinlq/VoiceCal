import { request } from '@/utils/request.js'

/**
 * POST /api/agent/text（需 Bearer JWT）
 * @returns {Promise<{session_id:string,reply_text:string,intent:string}>}
 */
export function sendAgentText({ sessionId, text }) {
  return request({
    url: '/agent/text',
    method: 'POST',
    data: {
      session_id: sessionId,
      text,
    },
    raw: true,
  })
}
