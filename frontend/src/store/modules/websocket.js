import { defineStore } from "pinia";
import { WS_BASE_URL } from "@/config/api.js";

const WS_URL_STORAGE_KEY = "voice_ws_url";

function getInitialWsUrl() {
  try {
    return uni.getStorageSync(WS_URL_STORAGE_KEY) || WS_BASE_URL;
  } catch {
    return WS_BASE_URL;
  }
}

/** 去掉已有 query，避免重复拼接 */
function stripQuery(url) {
  const idx = url.indexOf("?");
  return idx >= 0 ? url.slice(0, idx) : url;
}

function buildWsUrl(base, token) {
  const root = stripQuery(base);
  return `${root}?token=${encodeURIComponent(token)}`;
}

export const useWebSocketStore = defineStore("websocket", {
  state: () => ({
    connected: false,
    connecting: false,
    socketTask: null,
    serverUrl: getInitialWsUrl(),
    messageHandler: null,
    onCloseHandler: null,
  }),

  actions: {
    setMessageHandler(handler) {
      this.messageHandler = handler;
    },

    setOnCloseHandler(handler) {
      this.onCloseHandler = handler;
    },

    setServerUrl(url) {
      this.serverUrl = url || WS_BASE_URL;
      try {
        uni.setStorageSync(WS_URL_STORAGE_KEY, this.serverUrl);
      } catch (_) {}
    },

    resetServerUrl() {
      this.setServerUrl(WS_BASE_URL);
    },

    connect(token) {
      if (!token) {
        return Promise.reject(new Error("未登录，无法连接语音服务"));
      }

      if (this.connected && this.socketTask) {
        return Promise.resolve();
      }
      if (this.connecting) {
        return new Promise((resolve, reject) => {
          const check = setInterval(() => {
            if (this.connected) {
              clearInterval(check);
              resolve();
            }
            if (!this.connecting) {
              clearInterval(check);
              reject(new Error("WebSocket 连接失败"));
            }
          }, 100);
        });
      }

      const url = buildWsUrl(this.serverUrl, token);

      return new Promise((resolve, reject) => {
        this.connecting = true;

        const task = uni.connectSocket({
          url,
          fail: (err) => {
            this.connecting = false;
            reject(err);
          },
        });

        this.socketTask = task;

        task.onOpen(() => {
          this.connected = true;
          this.connecting = false;
          console.log("[ws] connected", url);
          resolve();
        });

        task.onMessage((res) => {
          try {
            const msg = JSON.parse(res.data);
            console.log("[ws] ←", msg.type, msg);
            this.messageHandler?.(msg);
          } catch (e) {
            console.error("[ws] invalid json", e, res.data);
          }
        });

        task.onClose((evt) => {
          console.log("[ws] closed", evt?.code, evt?.reason);
          this.connected = false;
          this.connecting = false;
          this.socketTask = null;
          this.onCloseHandler?.();
        });

        task.onError((err) => {
          console.error("[ws] error", err);
          this.connecting = false;
          if (!this.connected) reject(err);
        });
      });
    },

    send(payload) {
      if (!this.socketTask || !this.connected) {
        console.warn("[ws] not connected, drop message", payload?.type);
        return false;
      }
      console.log("[ws] →", payload.type);
      this.socketTask.send({
        data: JSON.stringify(payload),
        fail: (err) => console.error("[ws] send fail", err),
      });
      return true;
    },

    disconnect() {
      if (this.socketTask) {
        try {
          this.socketTask.close({
            code: 1000,
            reason: "normal",
          });
        } catch (_) {}
        this.socketTask = null;
      }
      this.connected = false;
      this.connecting = false;
    },
  },
});
