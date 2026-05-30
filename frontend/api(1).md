# VoiceCal（声历 Agent）API 文档

更新时间：2026-05-30  
后端实现位置：`backend/app`

> 本文档以当前代码实现为准，覆盖 `backend/app/main.py` 已注册的全部 HTTP / WebSocket 接口。

## 1. 基本信息

- 默认服务地址：`http://localhost:8000`
- OpenAPI：
  - Swagger UI：`GET /docs`
  - OpenAPI JSON：`GET /openapi.json`
  - ReDoc：`GET /redoc`
- 内容类型：
  - HTTP：`application/json`
  - WebSocket：JSON 文本帧

当前已注册接口：

- `GET /api/health`
- `POST /api/auth/wechat-login`
- `POST /api/auth/dev-login`
- `POST /api/agent/text`
- `GET /api/events`
- `POST /api/events`
- `GET /api/events/{event_id}`
- `PUT /api/events/{event_id}`
- `DELETE /api/events/{event_id}`
- `POST /api/wechat/subscribe-result`
- `GET /ws/voice`（WebSocket）

## 2. 鉴权规则

### 2.1 HTTP 鉴权

以下接口需要请求头：

```http
Authorization: Bearer <jwt_token>
```

需要鉴权的接口：

- `/api/agent/text`
- `/api/events*`
- `/api/wechat/subscribe-result`

无需鉴权的接口：

- `/api/health`
- `/api/auth/wechat-login`
- `/api/auth/dev-login`

说明：

- JWT 载荷里实际使用的是 `openid`
- 即使某些请求体里带了 `user_id` 字段，服务端最终仍以 JWT 中的身份为准

### 2.2 WebSocket 鉴权

连接地址：

```text
ws://localhost:8000/ws/voice?token=<jwt_token>
```

兼容模式：

```text
ws://localhost:8000/ws/voice?user_id=<openid>
```

注意：

- 优先使用 `token`
- `user_id` 只是兼容旧调用方式
- 缺少有效身份时，连接会在握手阶段被拒绝，关闭码为 `4001`

## 3. HTTP 通用返回

除 `/api/auth/*` 和 `/api/agent/text` 外，其它 HTTP 接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": null
}
```

规则：

- `code = 0`：成功
- `code != 0`：业务错误
- 某些业务错误会体现在响应体里，而不是 HTTP 状态码里

例如日程不存在时：

```json
{
  "code": 404,
  "message": "日程不存在",
  "data": null
}
```

但 HTTP 状态码仍通常是 `200`。

## 4. 健康检查

### `GET /api/health`

是否鉴权：否

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "running"
  }
}
```

## 5. 登录鉴权

### `POST /api/auth/wechat-login`

是否鉴权：否

请求体：

```json
{
  "code": "wx_login_code"
}
```

响应体：

```json
{
  "token": "<jwt_token>",
  "user": {
    "openid": "oMockWechatUser001",
    "unionid": "unionid-001"
  }
}
```

说明：

- 服务端会调用微信 `jscode2session`
- 若微信返回失败，接口会返回 HTTP `401`

### `POST /api/auth/dev-login`

是否鉴权：否

请求体：

```json
{
  "openid": "oTestUser001"
}
```

响应体：

```json
{
  "token": "<jwt_token>",
  "user": {
    "openid": "oTestUser001"
  }
}
```

说明：

- 仅非生产环境可用
- 生产环境会返回 HTTP `403`

## 6. Agent 文本调试

### `POST /api/agent/text`

是否鉴权：是

请求头：

```http
Authorization: Bearer <jwt_token>
```

请求体：

```json
{
  "session_id": "s_001",
  "user_id": "ignored_by_server",
  "text": "帮我明天下午三点加个会议"
}
```

说明：

- `user_id` 字段当前仅为兼容字段
- 服务端实际使用 JWT 中的 `openid`

响应体：

```json
{
  "session_id": "s_001",
  "intent": "",
  "slots": {},
  "tool_calls": [],
  "reply_text": "这个时间你已经有安排了，还要继续添加吗？"
}
```

字段说明：

- `session_id`：会话 ID
- `intent`：当前实现可能为空字符串
- `slots`：结构化槽位
- `tool_calls`：工具调用结果列表
- `reply_text`：给用户的最终回复文本

错误行为：

- 缺少或错误的 `Authorization`：HTTP `401`
- 处理链路异常：通常返回 HTTP `500`

## 7. 日程 Events API

前缀：`/api/events`

是否鉴权：是

### 7.1 事件对象

响应里的事件对象结构：

```json
{
  "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
  "user_id": "oTest_user_a_001",
  "title": "项目会议",
  "description": "讨论里程碑",
  "location": "会议室 A",
  "start_time": "2026-05-30T15:00:00",
  "end_time": "2026-05-30T16:00:00",
  "is_all_day": false,
  "completed": false,
  "remind_at": null,
  "remind_enabled": false,
  "push_status": "pending",
  "pushed_at": null,
  "subscribe_template_id": null,
  "created_at": "2026-05-30T10:00:00",
  "updated_at": "2026-05-30T10:00:00"
}
```

时间说明：

- 请求体中的时间字段使用 ISO 8601
- 当前服务端会按 `Asia/Shanghai` 语义落库为无时区 `datetime`

### 7.2 `GET /api/events`

查询参数：

- `start`：可选，ISO 8601 开始时间
- `end`：可选，ISO 8601 结束时间

示例：

```http
GET /api/events?start=2026-05-30T00:00:00&end=2026-05-30T23:59:59
Authorization: Bearer <jwt_token>
```

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
      "user_id": "oTest_user_a_001",
      "title": "项目会议",
      "description": null,
      "location": null,
      "start_time": "2026-05-30T15:00:00",
      "end_time": "2026-05-30T16:00:00",
      "is_all_day": false,
      "completed": false,
      "remind_at": null,
      "remind_enabled": false,
      "push_status": "pending",
      "pushed_at": null,
      "subscribe_template_id": null,
      "created_at": "2026-05-30T10:00:00",
      "updated_at": "2026-05-30T10:00:00"
    }
  ]
}
```

补充：

- 当前实现按用户隔离数据
- 测试覆盖显示：未完成事件排在前面，已完成事件排在后面

### 7.3 `POST /api/events`

请求体：

```json
{
  "title": "项目会议",
  "description": "讨论里程碑",
  "location": "会议室 A",
  "start_time": "2026-05-30T15:00:00+08:00",
  "end_time": "2026-05-30T16:00:00+08:00",
  "is_all_day": false,
  "completed": false,
  "remind_at": "2026-05-30T14:30:00+08:00",
  "remind_enabled": true,
  "subscribe_template_id": "template_001"
}
```

响应示例：

```json
{
  "code": 0,
  "message": "日程已创建",
  "data": {
    "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
    "user_id": "oTest_user_a_001",
    "title": "项目会议",
    "description": "讨论里程碑",
    "location": "会议室 A",
    "start_time": "2026-05-30T15:00:00",
    "end_time": "2026-05-30T16:00:00",
    "is_all_day": false,
    "completed": false,
    "remind_at": "2026-05-30T14:30:00",
    "remind_enabled": true,
    "push_status": "pending",
    "pushed_at": null,
    "subscribe_template_id": "template_001",
    "created_at": "2026-05-30T10:00:00",
    "updated_at": "2026-05-30T10:00:00"
  }
}
```

### 7.4 `GET /api/events/{event_id}`

路径参数：

- `event_id`：UUID

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
    "user_id": "oTest_user_a_001",
    "title": "项目会议",
    "description": null,
    "location": null,
    "start_time": "2026-05-30T15:00:00",
    "end_time": "2026-05-30T16:00:00",
    "is_all_day": false,
    "completed": false,
    "remind_at": null,
    "remind_enabled": false,
    "push_status": "pending",
    "pushed_at": null,
    "subscribe_template_id": null,
    "created_at": "2026-05-30T10:00:00",
    "updated_at": "2026-05-30T10:00:00"
  }
}
```

不存在时：

```json
{
  "code": 404,
  "message": "日程不存在",
  "data": null
}
```

### 7.5 `PUT /api/events/{event_id}`

请求体字段均可选：

```json
{
  "title": "项目会议（更新）",
  "description": "改到大会议室",
  "location": "会议室 B",
  "start_time": "2026-05-30T16:00:00+08:00",
  "end_time": "2026-05-30T17:00:00+08:00",
  "is_all_day": false,
  "completed": true,
  "remind_at": "2026-05-30T15:30:00+08:00",
  "remind_enabled": true,
  "push_status": "sent",
  "subscribe_template_id": "template_001"
}
```

成功响应：

```json
{
  "code": 0,
  "message": "日程已更新",
  "data": {
    "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
    "user_id": "oTest_user_a_001",
    "title": "项目会议（更新）",
    "description": "改到大会议室",
    "location": "会议室 B",
    "start_time": "2026-05-30T16:00:00",
    "end_time": "2026-05-30T17:00:00",
    "is_all_day": false,
    "completed": true,
    "remind_at": "2026-05-30T15:30:00",
    "remind_enabled": true,
    "push_status": "sent",
    "pushed_at": null,
    "subscribe_template_id": "template_001",
    "created_at": "2026-05-30T10:00:00",
    "updated_at": "2026-05-30T10:05:00"
  }
}
```

### 7.6 `DELETE /api/events/{event_id}`

成功响应：

```json
{
  "code": 0,
  "message": "日程已删除",
  "data": null
}
```

不存在时：

```json
{
  "code": 404,
  "message": "日程不存在",
  "data": null
}
```

## 8. 微信订阅消息授权结果

### `POST /api/wechat/subscribe-result`

是否鉴权：是

请求体：

```json
{
  "template_id": "template_001",
  "status": "accept"
}
```

`status` 当前约定值：

- `accept`
- `reject`
- `ban`

响应示例：

```json
{
  "code": 0,
  "message": "订阅状态已保存",
  "data": null
}
```

说明：

- 服务端会按 `(user_id, template_id)` 做 UPSERT

## 9. WebSocket 语音链路

### 9.1 连接方式

推荐：

```text
ws://localhost:8000/ws/voice?token=<jwt_token>
```

兼容：

```text
ws://localhost:8000/ws/voice?user_id=<openid>
```

协议特征：

- 全部使用 JSON 文本帧
- 不发送二进制帧
- 音频数据通过 base64 放在 JSON 字段里

### 9.2 客户端到服务端消息

### `text.message`

```json
{
  "type": "text.message",
  "session_id": "s_001",
  "text": "我明天有什么安排？"
}
```

说明：

- 直接跳过 ASR，把文本交给 Agent

### `audio_start`

```json
{
  "type": "audio_start",
  "session_id": "s_001",
  "format": "pcm_s16le",
  "sampleRate": 16000
}
```

说明：

- 建议发送
- 会清空服务端当前音频缓冲区
- 当前实现仅记录 `format/sampleRate`，不做强校验

### `audio.chunk`

```json
{
  "type": "audio.chunk",
  "session_id": "s_001",
  "data": "<base64_pcm_bytes>"
}
```

说明：

- `data` 为 base64 编码后的 PCM 音频字节
- 单片大于 `128KB` 会被记 warning

### `audio.end`

```json
{
  "type": "audio.end",
  "session_id": "s_001",
  "sample_rate": 16000
}
```

兼容别名：

- `audio_end`

说明：

- 收到后开始 ASR
- 当前实现只在 `audio.end` 后返回一次完整转写
- 不支持 partial ASR 推送

### 9.3 服务端到客户端消息

### `transcription`

```json
{
  "type": "transcription",
  "text": "明天下午三点开项目会议"
}
```

### `agent.reply`

```json
{
  "type": "agent.reply",
  "text": "这个时间你已经有安排了，还要继续添加吗？",
  "need_confirm": true
}
```

说明：

- `need_confirm = true` 表示当前轮需要用户继续确认
- 当前协议没有独立的 `confirm/cancel` 消息类型，继续对话仍走自然语言输入

### `tts.chunk`

```json
{
  "type": "tts.chunk",
  "data": "<base64_audio_bytes>",
  "is_last": false
}
```

说明：

- `data` 为 base64 编码后的音频字节
- `is_last = true` 表示该轮最后一个音频分片
- 当 Agent 侧启用实时流式语音时，`tts.chunk` 可能先于 `agent.reply` 到达

### `turn.done`

```json
{
  "type": "turn.done",
  "success": true
}
```

说明：

- 表示当前一轮处理结束

### `error`

```json
{
  "type": "error",
  "message": "invalid json"
}
```

常见错误：

- `invalid json`
- `empty text`
- `invalid base64 audio data`
- `asr error: ...`
- `agent error: ...`
- `unknown message type: ...`

## 10. 联调建议

推荐联调顺序：

1. 先调用 `POST /api/auth/dev-login` 拿测试 JWT
2. 用该 JWT 调 `GET /api/events` 验证 HTTP 鉴权
3. 再用 `ws://localhost:8000/ws/voice?token=<jwt_token>` 验证 WebSocket

如果只需要看机器生成的接口定义，可直接打开：

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
