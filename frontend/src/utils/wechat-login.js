const STORAGE_KEY = "wechat_login_info";

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
 * 将 code 交给后端换取 openid / token
 * @param {string} code
 */
export function exchangeCodeWithBackend(code) {
  const apiBase = import.meta.env.VITE_API_URL || "";
  if (!apiBase) {
    return Promise.resolve(null);
  }

  const url = `${apiBase.replace(/\/$/, "")}/auth/weixin/silent-login`;

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: "POST",
      data: { code },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data) {
          resolve(res.data);
          return;
        }
        reject(
          new Error(
            res.data?.message || `后端登录失败（${res.statusCode || "unknown"}）`,
          ),
        );
      },
      fail: (err) => {
        reject(new Error(err.errMsg || "请求后端登录接口失败"));
      },
    });
  });
}

/**
 * 微信静默登录：优先复用有效 session，否则重新 login 获取 code
 * @returns {Promise<object>}
 */
export async function wechatSilentLogin() {
  if (!isMpWeixin()) {
    throw new Error("当前非微信小程序环境，无法执行微信静默登录");
  }

  const sessionValid = await checkWechatSession();
  const cached = getCachedLoginInfo();

  if (sessionValid && cached?.openid) {
    const info = {
      ...cached,
      fromCache: true,
      sessionValid: true,
      loginTime: cached.loginTime || new Date().toISOString(),
    };
    setCachedLoginInfo(info);
    return info;
  }

  const { code } = await getWechatLoginCode();
  const loginTime = new Date().toISOString();

  let backendData = null;
  try {
    backendData = await exchangeCodeWithBackend(code);
  } catch (error) {
    console.warn("[微信静默登录] 后端换取用户信息失败，仅保留 code", error);
  }

  const loginInfo = {
    code,
    openid: backendData?.openid || cached?.openid || "",
    unionid: backendData?.unionid || cached?.unionid || "",
    token: backendData?.token || cached?.token || "",
    sessionKey: backendData?.session_key || backendData?.sessionKey || "",
    nickName: backendData?.nickName || cached?.nickName || "",
    avatarUrl: backendData?.avatarUrl || cached?.avatarUrl || "",
    loginTime,
    sessionValid: true,
    fromCache: false,
    platform: "mp-weixin",
    silent: true,
    backendReady: Boolean(backendData),
  };

  setCachedLoginInfo(loginInfo);
  return loginInfo;
}
