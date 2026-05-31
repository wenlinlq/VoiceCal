const LAN_TEST_HOST = "127.0.0.1:8000";
const PROD_HOST = "latekin.jufu.vip";

/** 联调地址 */
export const API_BASE_URL = `https://${PROD_HOST}/api`;

/** 联调 WebSocket 地址 */
export const WS_BASE_URL = `wss://${PROD_HOST}/ws/voice`;

/** 微信订阅消息模板 ID */
export const SUBSCRIBE_TEMPLATE_ID =
  import.meta.env.VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID || "";
