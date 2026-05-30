import { defineStore } from "pinia";
import {
  getCachedLoginInfo,
  hasValidCachedLoginContext,
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
    apiBase: "",
    mpWeixinAppId: "",
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
        apiBase: state.apiBase,
        mpWeixinAppId: state.mpWeixinAppId,
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
      this.apiBase = info.apiBase || "";
      this.mpWeixinAppId = info.mpWeixinAppId || "";
      this.isLoggedIn = Boolean(this.token);
      this.loginError = "";
    },

    restoreFromCache() {
      const cached = getCachedLoginInfo();
      if (cached && hasValidCachedLoginContext(cached)) {
        this.applyLoginInfo(cached);
        return;
      }
      this.clearLogin();
    },

    async silentLogin() {
      const info = await wechatSilentLogin();
      this.applyLoginInfo(info);
      setCachedLoginInfo(this.loginInfo);
      return this.loginInfo;
    },

    /** 确保已拿到 JWT（启动时调用） */
    async ensureAuth() {
      if (this.token && hasValidCachedLoginContext(this.loginInfo)) {
        return this.loginInfo;
      }
      return this.silentLogin();
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
