/**
 * @typedef {Object} UserLoginInfo
 * @property {boolean} isLoggedIn
 * @property {string} openid
 * @property {string} [unionid]
 * @property {string} [token]
 * @property {string} code
 * @property {string} [sessionKey]
 * @property {string} [nickName]
 * @property {string} [avatarUrl]
 * @property {string} loginTime
 * @property {boolean} sessionValid
 * @property {boolean} fromCache
 * @property {boolean} backendReady
 * @property {string} platform
 * @property {boolean} silent
 */

/**
 * @typedef {Object} Event
 * @property {number} [id] - 事件ID
 * @property {string} title - 事件标题
 * @property {string} start_time - 开始时间 (YYYY-MM-DD HH:MM:SS)
 * @property {string} [end_time] - 结束时间
 * @property {'none'|'daily'|'weekly'|'monthly'} repeat_type - 重复类型
 * @property {string} [note] - 备注
 * @property {boolean} [completed] - 是否已完成
 * @property {string} [created_at] - 创建时间
 */

/**
 * @typedef {('idle'|'recording'|'processing'|'speaking'|'waiting_confirm')} WSStatus
 */

/**
 * @typedef {('listening'|'thinking'|'speaking'|'waiting_confirm')} AgentState
 */

export {}
