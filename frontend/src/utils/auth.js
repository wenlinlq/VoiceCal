import { getCachedLoginInfo } from "@/utils/wechat-login.js";

/** 从本地缓存读取 JWT（供 request / WebSocket 使用，避免 Pinia 循环依赖） */
export function getAuthToken() {
  const cached = getCachedLoginInfo();
  return cached?.token || "";
}

export function getAuthOpenid() {
  const cached = getCachedLoginInfo();
  return cached?.openid || "";
}
