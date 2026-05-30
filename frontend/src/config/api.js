const API_HOST = import.meta.env.VITE_API_HOST || "218.244.137.52";
const API_PORT = import.meta.env.VITE_API_PORT || "8000";

/** HTTP API 根路径，例如 http://218.244.137.52:8000/api */
export const API_BASE_URL =
  import.meta.env.VITE_API_URL || `http://${API_HOST}:${API_PORT}/api`;

/** WebSocket 语音地址，例如 ws://218.244.137.52:8000/ws/voice */
export const WS_BASE_URL =
  import.meta.env.VITE_WS_URL || `ws://${API_HOST}:${API_PORT}/ws/voice`;
