import { defineStore } from "pinia";
import {
  getCachedLoginInfo,
  setCachedLoginInfo,
  wechatSilentLogin,
} from "@/utils/wechat-login.js";

export const useUserStore = defineStore("user", {
  state: () => ({
    isLoggedIn: false,
    openid: "",
    unionid: "",
    token: "",
    code: "",
    sessionKey: "",
    nickName: "",
    avatarUrl: "",
    loginTime: "",
    sessionValid: false,
    fromCache: false,
    backendReady: false,
    platform: "",
    silent: true,
    loginError: "",
  }),

  getters: {
    loginInfo(state) {
      return {
        isLoggedIn: state.isLoggedIn,
        openid: state.openid,
        unionid: state.unionid,
        token: state.token,
        code: state.code,
        sessionKey: state.sessionKey,
        nickName: state.nickName,
        avatarUrl: state.avatarUrl,
        loginTime: state.loginTime,
        sessionValid: state.sessionValid,
        fromCache: state.fromCache,
        backendReady: state.backendReady,
        platform: state.platform,
        silent: state.silent,
      };
    },
  },

  actions: {
    applyLoginInfo(info = {}) {
      this.openid = info.openid || "";
      this.unionid = info.unionid || "";
      this.token = info.token || "";
      this.code = info.code || "";
      this.sessionKey = info.sessionKey || "";
      this.nickName = info.nickName || "";
      this.avatarUrl = info.avatarUrl || "";
      this.loginTime = info.loginTime || "";
      this.sessionValid = Boolean(info.sessionValid);
      this.fromCache = Boolean(info.fromCache);
      this.backendReady = Boolean(info.backendReady);
      this.platform = info.platform || "";
      this.silent = info.silent !== false;
      this.isLoggedIn = Boolean(this.openid || this.code || this.token);
      this.loginError = "";
    },

    restoreFromCache() {
      const cached = getCachedLoginInfo();
      if (cached) {
        this.applyLoginInfo(cached);
      }
    },

    async silentLogin() {
      const info = await wechatSilentLogin();
      this.applyLoginInfo(info);
      setCachedLoginInfo(this.loginInfo);
      return this.loginInfo;
    },

    clearLogin() {
      this.applyLoginInfo({});
      this.isLoggedIn = false;
      this.loginError = "";
      uni.removeStorageSync("wechat_login_info");
    },

    setLoginError(message) {
      this.loginError = message || "";
    },
  },
});
