import { API_BASE_URL } from "@/config/api.js";
import { devLogin, wechatLogin } from "@/api/auth.js";

const STORAGE_KEY = "wechat_login_info";

const DEV_OPENID = import.meta.env.VITE_DEV_OPENID || "";

/**
 * 是否微信小程序环境
 */
export function isMpWeixin() {
  // #ifdef MP-WEIXIN
  return true;
  // #endif
  // #ifndef MP-WEIXIN
  return false;
  // #endif
}

/**
 * 读取本地缓存的登录信息
 * @returns {object|null}
 */
export function getCachedLoginInfo() {
  try {
    return uni.getStorageSync(STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

/**
 * 缓存登录信息
 * @param {object} info
 */
export function setCachedLoginInfo(info) {
  uni.setStorageSync(STORAGE_KEY, info);
}

/**
 * 调用 wx.login 获取临时 code（静默，无需用户授权）
 * @returns {Promise<{ code: string }>}
 */
export function getWechatLoginCode() {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: "weixin",
      success: (res) => {
        if (res.code) {
          resolve({ code: res.code });
          return;
        }
        reject(new Error(res.errMsg || "未获取到微信登录 code"));
      },
      fail: (err) => {
        reject(new Error(err.errMsg || "微信登录失败"));
      },
    });
  });
}

/**
 * 检查微信 session 是否仍有效
 * @returns {Promise<boolean>}
 */
export function checkWechatSession() {
  return new Promise((resolve) => {
    uni.checkSession({
      success: () => resolve(true),
      fail: () => resolve(false),
    });
  });
}

/**
 * 将后端登录结果写入统一结构
 * @param {{ token: string, user: { openid: string, unionid?: string } }} authData
 * @param {object} [extra]
 */
function buildLoginInfo(authData, extra = {}) {
  const user = authData?.user || {};
  return {
    openid: user.openid || "",
    unionid: user.unionid || "",
    token: authData?.token || "",
    loginTime: new Date().toISOString(),
    sessionValid: true,
    fromCache: false,
    backendReady: true,
    platform: extra.platform || "",
    silent: extra.silent !== false,
    code: extra.code || "",
  };
}

/**
 * 开发环境登录（H5 / 非微信端）
 */
export async function devSilentLogin(openid = DEV_OPENID) {
  if (!openid) {
    throw new Error(
      "非微信环境请配置 VITE_DEV_OPENID 以使用 dev-login，或在微信小程序中运行",
    );
  }
  const authData = await devLogin(openid);
  const info = buildLoginInfo(authData, {
    platform: "dev",
    silent: true,
  });
  setCachedLoginInfo(info);
  return info;
}

/**
 * 微信静默登录：优先复用有效 session + JWT，否则重新 login 换取 token
 * @returns {Promise<object>}
 */
export async function wechatSilentLogin() {
  if (!isMpWeixin()) {
    return devSilentLogin();
  }

  const sessionValid = await checkWechatSession();
  const cached = getCachedLoginInfo();

  if (sessionValid && cached?.token && cached?.openid) {
    const info = {
      ...cached,
      fromCache: true,
      sessionValid: true,
      loginTime: cached.loginTime || new Date().toISOString(),
      backendReady: true,
      platform: "mp-weixin",
    };
    setCachedLoginInfo(info);
    return info;
  }

  const { code } = await getWechatLoginCode();
  const authData = await wechatLogin(code);
  const loginInfo = buildLoginInfo(authData, {
    platform: "mp-weixin",
    silent: true,
    code,
  });

  setCachedLoginInfo(loginInfo);
  return loginInfo;
}
