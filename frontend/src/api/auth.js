import { request } from "@/utils/request.js";

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
