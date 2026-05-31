import { defineStore } from "pinia";

/** 语音状态：idle → recording → thinking → speaking → auto_listening → idle */
export const VOICE_STATUS = {
  IDLE: "idle",
  RECORDING: "recording",
  THINKING: "thinking",
  SPEAKING: "speaking",
  AUTO_LISTENING: "auto_listening",
};

export const useVoiceStore = defineStore("voice", {
  state: () => ({
    status: VOICE_STATUS.IDLE,
    sessionOpen: false,
    sessionId: "",
    userText: "",
    replyText: "",
    errorText: "",
    needConfirm: false,
    queryListenMode: false,
    asrText: "",
    asrTempText: "",
  }),

  getters: {
    panelText(state) {
      return state.replyText || state.errorText || "";
    },
    displayText(state) {
      return (
        state.replyText ||
        state.errorText ||
        state.userText ||
        state.asrTempText ||
        state.asrText
      );
    },
    isActive(state) {
      return state.status !== VOICE_STATUS.IDLE || state.sessionOpen;
    },
    isListening(state) {
      return (
        state.status === VOICE_STATUS.RECORDING ||
        state.status === VOICE_STATUS.AUTO_LISTENING
      );
    },
  },

  actions: {
    setStatus(status) {
      this.status = status;
    },

    openSession() {
      this.sessionOpen = true;
    },

    closeSession() {
      this.sessionOpen = false;
    },

    setSessionId(id) {
      this.sessionId = id;
    },

    setUserText(text) {
      this.userText = text || "";
      this.asrText = text || "";
      this.asrTempText = "";
    },

    setReplyText(text, needConfirm = false) {
      this.replyText = text || "";
      this.needConfirm = Boolean(needConfirm);
      this.errorText = "";
    },

    setQueryListenMode(enabled) {
      this.queryListenMode = Boolean(enabled);
    },

    setError(message) {
      this.errorText = message || "语音服务异常";
      this.replyText = "";
    },

    /** 用户新一轮输入已提交，等待 Agent 回复前清空上轮展示文案 */
    beginAgentTurn() {
      this.replyText = "";
      this.userText = "";
      this.errorText = "";
      this.asrText = "";
      this.asrTempText = "";
    },

    clearTurn() {
      this.beginAgentTurn();
      this.needConfirm = false;
      this.queryListenMode = false;
    },

    reset() {
      this.status = VOICE_STATUS.IDLE;
      this.sessionOpen = false;
      this.sessionId = "";
      this.clearTurn();
    },
  },
});
