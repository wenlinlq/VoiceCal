const LAN_TEST_HOST = "10.4.137.31:8000";
// const PROD_HOST = "latekin.jufu.vip"; // 上线时切回域名

/** 真机联调地址 */
export const API_BASE_URL = `http://${LAN_TEST_HOST}/api`;

/** 真机联调 WebSocket 地址 */
export const WS_BASE_URL = `ws://${LAN_TEST_HOST}/ws/voice`;

/** 微信订阅消息模板 ID */
export const SUBSCRIBE_TEMPLATE_ID =
  import.meta.env.VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID || "";
