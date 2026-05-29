import { defineStore } from 'pinia'

export const useVoiceStore = defineStore('voice', {
  state: () => ({
    status: 'idle',
    asrText: '',
    asrTempText: ''
  }),

  getters: {
    displayText(state) {
      return state.asrTempText || state.asrText
    },
    isActive(state) {
      return state.status !== 'idle'
    }
  },

  actions: {
    setStatus(status) {
      this.status = status
    },

    setAsrText(text, isFinal) {
      if (isFinal) {
        this.asrText = text
        this.asrTempText = ''
      } else {
        this.asrTempText = text
      }
    },

    reset() {
      this.status = 'idle'
      this.asrText = ''
      this.asrTempText = ''
    }
  }
})
