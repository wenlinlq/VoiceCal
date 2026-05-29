import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    connected: false,
    reconnecting: false,
    reconnectCount: 0,
    serverUrl: 'ws://localhost:8080/ws/voice'
  }),

  actions: {
    connect() {
      // 静态阶段：模拟连接
      this.connected = true
    },

    disconnect() {
      this.connected = false
    },

    sendAudio() {},

    sendControl() {}
  }
})
