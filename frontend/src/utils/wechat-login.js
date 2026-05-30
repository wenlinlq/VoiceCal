import { API_BASE_URL } from "@/config/api.js";
import { devLogin, wechatLogin } from "@/api/auth.js";

const STORAGE_KEY = "wechat_login_info";

/** H5 / 其它端联调：POST /api/auth/dev-login 使用的 openid */
export const DEV_OPENID = import.meta.env.VITE_DEV_OPENID || "";

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
 * 是否 H5 等非小程序端（编译期分支）
 */
export function isH5() {
  // #ifdef H5
  return true;
  // #endif
  // #ifndef H5
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
 * H5 等环境：POST /api/auth/dev-login 换取 JWT
 * @param {string} [openid]
 */
export async function devSilentLogin(openid) {
  const id = String(openid ?? DEV_OPENID).trim();
  if (!id) {
    throw new Error(
      "H5 请在 .env.local 配置 VITE_DEV_OPENID，或在设置页填写 openid 后登录",
    );
  }
  const authData = await devLogin(id);
  const info = buildLoginInfo(authData, {
    platform: "h5-dev",
    silent: true,
  });
  setCachedLoginInfo(info);
  return info;
}

/** 从缓存恢复 JWT（有 token 即视为已登录） */
export function getCachedAuthIfValid() {
  const cached = getCachedLoginInfo();
  if (!cached?.token || !cached?.openid) return null;
  return {
    ...cached,
    fromCache: true,
    sessionValid: true,
    backendReady: true,
  };
}

/**
 * 按当前平台登录并拿到 token
 * - 小程序：wx.login → POST /api/auth/wechat-login
 * - H5：POST /api/auth/dev-login（须配置或传入 openid）
 */
export async function loginForCurrentPlatform(openid) {
  if (isMpWeixin()) {
    return wechatSilentLogin();
  }
  const cached = getCachedAuthIfValid();
  if (cached && !openid) {
    setCachedLoginInfo(cached);
    return cached;
  }
  return devSilentLogin(openid);
}

/**
 * 微信静默登录：优先复用有效 session + JWT，否则重新 login 换取 token
 * @returns {Promise<object>}
 */
export async function wechatSilentLogin() {
  if (!isMpWeixin()) {
    return loginForCurrentPlatform();
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
