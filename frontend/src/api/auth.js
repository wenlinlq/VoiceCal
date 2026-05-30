import { request } from "@/utils/request.js";

/**
 * 鉴权 token 获取方式（见 api(1).md §5）：
 *
 * 微信小程序：
 *   uni.login() → code → POST /api/auth/wechat-login → { token, user }
 *
 * H5 / 浏览器：
 *   POST /api/auth/dev-login { openid } → { token, user }
 *   openid 来自 VITE_DEV_OPENID 或设置页手动填写
 *
 * 拿到 token 后：
 *   - 存入 uni.storage（key: wechat_login_info）
 *   - HTTP：request.js 自动加 Authorization: Bearer <token>
 *   - WebSocket：/ws/voice?token=<jwt_token>
 */

/**
 * POST /api/auth/wechat-login
 * @param {string} code wx.login 临时 code
 * @returns {Promise<{ token: string, user: { openid: string, unionid?: string } }>}
 */
export function wechatLogin(code) {
  return request({
    url: "/auth/wechat-login",
    method: "POST",
    data: { code },
    skipAuth: true,
    authResponse: true,
  });
}

/**
 * POST /api/auth/dev-login（仅非生产环境）
 * @param {string} openid
 * @returns {Promise<{ token: string, user: { openid: string } }>}
 */
export function devLogin(openid) {
  return request({
    url: "/auth/dev-login",
    method: "POST",
    data: { openid },
    skipAuth: true,
    authResponse: true,
  });
}
