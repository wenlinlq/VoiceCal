import { API_BASE_URL } from "@/config/api.js";
import { getAuthToken } from "@/utils/auth.js";

/**
 * 统一 HTTP 请求
 * @param {object} options
 * @param {string} options.url 相对路径，如 /events
 * @param {'GET'|'POST'|'PUT'|'DELETE'} [options.method]
 * @param {object} [options.data] 请求体
 * @param {object} [options.query] 查询参数
 * @param {boolean} [options.raw] 为 true 时直接返回响应体（用于 /agent/text）
 * @param {boolean} [options.skipAuth] 为 true 时不附带 Authorization（登录、健康检查）
 * @param {boolean} [options.authResponse] 为 true 时解析 { token, user } 登录响应体
 */
export function request({
  url,
  method = "GET",
  data,
  query,
  raw = false,
  skipAuth = false,
  authResponse = false,
}) {
  const fullUrl = buildUrl(url, query);
  const headers = { "Content-Type": "application/json" };

  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: headers,
      success: (res) => {
        if (res.statusCode === 401) {
          reject(new Error(res.data?.detail || "未授权，请重新登录"));
          return;
        }

        if (res.statusCode < 200 || res.statusCode >= 300) {
          const msg =
            res.data?.detail ||
            res.data?.message ||
            `HTTP ${res.statusCode}`;
          reject(new Error(msg));
          return;
        }

        const body = res.data;

        if (authResponse) {
          if (body?.token) {
            resolve(body);
            return;
          }
          reject(new Error("登录响应缺少 token"));
          return;
        }

        if (raw) {
          resolve(body);
          return;
        }

        if (!body || typeof body !== "object") {
          reject(new Error("响应格式错误"));
          return;
        }

        if (body.code !== 0) {
          reject(new Error(body.message || `业务错误 code=${body.code}`));
          return;
        }

        resolve(body.data);
      },
      fail: (err) => {
        reject(new Error(err.errMsg || "网络请求失败"));
      },
    });
  });
}

function buildUrl(path, query) {
  const base = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  let url = `${base}${normalizedPath}`;

  if (query && Object.keys(query).length) {
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    if (qs) url += `?${qs}`;
  }

  return url;
}
