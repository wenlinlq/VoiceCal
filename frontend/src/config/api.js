/** 后端地址 */
const API_HOST = "https://latekin.jufu.vip";

/** API 地址 */
export const API_BASE_URL = `${API_HOST}/api`;

/** WebSocket 地址 */
export const WS_BASE_URL = API_HOST.replace(/^https/, "wss") + "/ws/voice";

/** 微信订阅消息模板 ID */
export const SUBSCRIBE_TEMPLATE_ID =
  import.meta.env.VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID || "";
