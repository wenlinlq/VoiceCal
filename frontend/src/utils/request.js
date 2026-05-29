import { API_BASE_URL } from '@/config/api.js'

/**
 * 统一 HTTP 请求
 * @param {object} options
 * @param {string} options.url 相对路径，如 /events
 * @param {'GET'|'POST'|'PUT'|'DELETE'} [options.method]
 * @param {object} [options.data] 请求体
 * @param {object} [options.query] 查询参数
 * @param {boolean} [options.raw] 为 true 时直接返回响应体（用于 /agent/text）
 */
export function request({
  url,
  method = 'GET',
  data,
  query,
  raw = false,
}) {
  const fullUrl = buildUrl(url, query)

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
      },
      success: (res) => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`HTTP ${res.statusCode}`))
          return
        }

        const body = res.data
        if (raw) {
          resolve(body)
          return
        }

        if (!body || typeof body !== 'object') {
          reject(new Error('响应格式错误'))
          return
        }

        if (body.code !== 0) {
          reject(new Error(body.message || `业务错误 code=${body.code}`))
          return
        }

        resolve(body.data)
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络请求失败'))
      },
    })
  })
}

function buildUrl(path, query) {
  const base = API_BASE_URL.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  let url = `${base}${normalizedPath}`

  if (query && Object.keys(query).length) {
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&')
    if (qs) url += `?${qs}`
  }

  return url
}
