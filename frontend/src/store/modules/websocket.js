import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    connected: false,
    reconnecting: false,
    reconnectCount: 0,
    serverUrl: 'ws://localhost:8000/ws/voice',
  }),

  actions: {
    connect() {
      this.connected = true
      return Promise.resolve()
    },

    disconnect() {
      this.connected = false
    },

    send() {},

    sendControl() {},
  },
})
