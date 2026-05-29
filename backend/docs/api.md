# VoiceCal（声历 Agent）接口文档（以当前代码实现为准）

更新时间：2026-05-29  
后端：FastAPI（`backend/app`）  

> 说明：仓库里已有的设计/规划文档 `backend/语音日历工具-后端开发与接口文档 .md` 包含“二进制 header 帧 / control action / partial ASR”等设想；而**当前后端实现**的 WebSocket 协议是“纯 JSON 消息 + 音频分片 base64”，并且 **ASR 只在 `audio.end` 后一次性返回转写结果**。本文档描述的是“跑起来即可联调”的实现版接口。

---

## 0. 基本信息

- 默认服务端口：`8000`（见 `backend/app/main.py`、`backend/docker-compose.yml`）
- OpenAPI（FastAPI 默认）：
  - Swagger UI：`GET /docs`
  - OpenAPI JSON：`GET /openapi.json`
  - ReDoc：`GET /redoc`
- 鉴权：当前无（MVP 默认用户多为 `demo_user`）
- 内容类型：HTTP 为 `application/json`；WebSocket 为 `text frame(JSON)`（不发送二进制帧）
- 时间格式：
  - REST 接口入参 `start_time/end_time`：ISO 8601 字符串（FastAPI 解析为 `datetime`）
  - 服务端存储：若传入带时区 `datetime`，会转为 `Asia/Shanghai`（UTC+8）再去掉 tzinfo（naive）后落库（见 `backend/app/services/calendar_service.py`）

---

## 1. 通用返回结构（HTTP）

除 `/api/agent/text` 外，其它 REST 接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": null
}
```

- `code=0` 表示成功
- 非 0 表示业务错误（例如查不到事件时返回 `code=404`）
- 注意：当前实现里 **即便 `code=404`，HTTP 状态码通常仍为 200**（因为未抛 `HTTPException`，而是返回了 `APIResponse.error(...)`）

---

## 2. 健康检查

### 2.1 `GET /api/health`

响应（示例）：

```json
{
  "code": 0,
  "message": "ok",
  "data": { "status": "running" }
}
```

---

## 3. Agent 文本调试接口

### 3.1 `POST /api/agent/text`

用途：跳过语音链路，直接用文本驱动 Agent（便于调试）。

请求体：

```json
{
  "session_id": "s_001",
  "user_id": "demo_user",
  "text": "帮我明天下午三点加个会议"
}
```

响应体（示例）：

```json
{
  "session_id": "s_001",
  "intent": "agent_scope",
  "slots": {},
  "tool_calls": [],
  "reply_text": "好的，已为你设置下午三点的会议。"
}
```

字段说明：

- `session_id`：会话 ID（由客户端生成）
- `user_id`：用户 ID（默认 `demo_user`）
- `reply_text`：Agent 给用户的最终回复文案
- 备注：当前适配层固定 `intent="agent_scope"`，`slots/tool_calls` 为空（见 `backend/app/agents/calendar_agent.py`）

错误：

- 可能返回 FastAPI 默认 `500` 错误结构（未做统一 `APIResponse` 包装）

---

## 4. 日程（Events）CRUD

前缀：`/api/events`

> 重要：当前 HTTP CRUD 接口未透传 `user_id`，因此所有数据实际都按 `demo_user` 隔离（见 `CalendarService(db, user_id="demo_user")`）。

### 4.1 `GET /api/events`

查询参数：

- `start`：可选，ISO 8601（查询开始时间）
- `end`：可选，ISO 8601（查询结束时间）

响应 `data`：`EventResponse[]`

`EventResponse`（示例）：

```json
{
  "id": "9d2a7e2f-5a7b-4f7a-9e1f-2a0b1d9a3c25",
  "user_id": "demo_user",
  "title": "项目会议",
  "description": null,
  "location": null,
  "start_time": "2026-05-30T15:00:00",
  "end_time": "2026-05-30T16:00:00",
  "is_all_day": false,
  "created_at": "2026-05-29T12:00:00",
  "updated_at": "2026-05-29T12:00:00"
}
```

### 4.2 `POST /api/events`

请求体：`EventCreate`

```json
{
  "title": "项目会议",
  "description": "讨论里程碑",
  "location": "会议室 A",
  "start_time": "2026-05-30T15:00:00+08:00",
  "end_time": "2026-05-30T16:00:00+08:00",
  "is_all_day": false
}
```

响应：`APIResponse.data = EventResponse`，并附带 `message="日程已创建"`。

### 4.3 `GET /api/events/{event_id}`

- `event_id`：UUID

不存在时返回（示例）：

```json
{ "code": 404, "message": "日程不存在", "data": null }
```

### 4.4 `PUT /api/events/{event_id}`

请求体：`EventUpdate`（字段均可选，仅更新传入字段）

```json
{
  "title": "项目会议（更新）",
  "start_time": "2026-05-30T16:00:00+08:00",
  "end_time": "2026-05-30T17:00:00+08:00"
}
```

成功返回 `message="日程已更新"`；不存在返回 `code=404`。

### 4.5 `DELETE /api/events/{event_id}`

成功返回 `message="日程已删除"`；不存在返回 `code=404`。

---

## 5. WebSocket：语音主链路

### 5.1 连接

- URL：`GET /ws/voice`
- Query：
  - `user_id`：可选，缺省为 `demo_user`

示例：`ws://localhost:8000/ws/voice?user_id=demo_user`

### 5.2 客户端 → 服务端消息

所有消息均为 JSON 文本帧，字段 `type` 决定消息类型。

#### 5.2.1 文本直通：`text.message`

```json
{
  "type": "text.message",
  "session_id": "s_001",
  "user_id": "demo_user",
  "text": "我明天有什么安排？"
}
```

#### 5.2.2 开始录音：`audio_start`（建议必发）

```json
{
  "type": "audio_start",
  "session_id": "s_001",
  "user_id": "demo_user",
  "format": "pcm_s16le",
  "sampleRate": 16000
}
```

说明：

- 当前实现不会校验 `format/sampleRate`，仅用于日志与未来扩展
- `audio_start` 会清空服务端音频缓冲区；若不发，可能导致缓冲区残留影响转写

#### 5.2.3 音频分片：`audio.chunk`

```json
{
  "type": "audio.chunk",
  "session_id": "s_001",
  "user_id": "demo_user",
  "data": "<base64 PCM bytes>"
}
```

音频要求（按当前 ASR 实现）：

- `data`：base64 后的原始 PCM bytes
- PCM：16-bit、mono（服务端在 `audio.end` 时会写 WAV 并调用 DashScope ASR；采样率会在服务端被重采样到 16k）
- 分片大小建议 < 128KB（大于该值会被记录为 warning）

#### 5.2.4 结束录音：`audio.end` / `audio_end`

```json
{
  "type": "audio.end",
  "session_id": "s_001",
  "user_id": "demo_user",
  "sample_rate": 16000
}
```

说明：

- `sample_rate` 默认 16000；若前端真实采样率不同，请传真实值，服务端会重采样到 16k 再识别
- 当前实现不会推送 ASR partial，只在收到 `audio.end` 后进行一次性识别

### 5.3 服务端 → 客户端消息

#### 5.3.1 转写结果：`transcription`

```json
{
  "type": "transcription",
  "text": "明天下午三点开项目会议"
}
```

#### 5.3.2 Agent 回复：`agent.reply`

```json
{
  "type": "agent.reply",
  "text": "这个时间你已经有安排了，还要继续添加吗？",
  "need_confirm": true
}
```

说明：

- `need_confirm=true` 表示 Agent 认为当前属于“需要用户确认”的多轮场景（例如冲突/歧义删除/修改）
- **当前 WebSocket 协议里没有实现显式 `confirm/cancel` 控制消息**；多轮继续依赖用户下一句自然语言（例如“继续”“取消”“那改到四点”）

#### 5.3.3 语音分片：`tts.chunk`

```json
{
  "type": "tts.chunk",
  "data": "<base64 audio bytes>",
  "is_last": false
}
```

说明（实现现状）：

- `data` 为 base64 编码的音频 bytes
- 主路径：来自 AgentScope 捕获的 `speech`（通常为 PCM bytes 分片）
- 兜底路径：独立 DashScope TTS 回调返回的音频分片 bytes（`format` 字段当前未在协议中携带）

#### 5.3.4 本轮结束：`turn.done`

```json
{
  "type": "turn.done",
  "success": true
}
```

#### 5.3.5 错误：`error`

```json
{
  "type": "error",
  "message": "asr error: ..."
}
```

常见错误场景：

- 非法 JSON：`invalid json`
- 空文本：`empty text`
- 非法 base64 音频：`invalid base64 audio data`
- ASR/Agent/TTS 处理异常：`asr error: ...` / `agent error: ...`

---

## 6. 与配置相关的注意事项（联调必看）

关键环境变量（见 `backend/app/core/config.py`）：

- `DASHSCOPE_API_KEY`：未设置时，ASR / TTS / Agent 模型调用可能失败（表现为 WS `error` 或 HTTP 500）
- `DATABASE_URL`：默认指向本地 Postgres；若要用 SQLite 需改为 async driver（例如 `sqlite+aiosqlite:///...`）

