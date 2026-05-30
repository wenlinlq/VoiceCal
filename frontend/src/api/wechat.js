import { request } from "@/utils/request.js";

/**
 * POST /api/wechat/subscribe-result
 * @param {{ template_id: string, status: 'accept' | 'reject' | 'ban' }} payload
 */
export function reportSubscribeResult(payload) {
  return request({
    url: "/wechat/subscribe-result",
    method: "POST",
    data: payload,
  });
}
