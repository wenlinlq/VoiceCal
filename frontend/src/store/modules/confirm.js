import { defineStore } from 'pinia'

export const useConfirmStore = defineStore('confirm', {
  state: () => ({
    visible: false,
    event: null,
    message: ''
  }),

  actions: {
    showConfirm(event, message) {
      this.event = event
      this.message = message
      this.visible = true
    },

    hideConfirm() {
      this.visible = false
      this.event = null
      this.message = ''
    },

    confirm() {
      this.hideConfirm()
    },

    cancel() {
      this.hideConfirm()
    }
  }
})
