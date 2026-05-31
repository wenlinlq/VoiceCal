# 语音日历 · 前端

uni-app + Vue 3 + Pinia 实现的语音日历小程序，支持月历浏览、日程 CRUD、以及通过 WebSocket 与后端 Agent 进行多轮语音对话。

## 技术栈

| 分类 | 技术                                 | 说明                                 |
| ---- | ------------------------------------ | ------------------------------------ |
| 框架 | uni-app 3.x                          | 主目标平台：微信小程序；可选 H5 联调 |
| UI   | Vue 3 Composition API                | `<script setup>`                     |
| 状态 | Pinia 2.x                            | `store/modules/*`                    |
| 构建 | Vite 5 + `@dcloudio/vite-plugin-uni` |                                      |
| 样式 | Sass                                 | 组件级 `.scss`                       |

## 快速开始

```bash
cd frontend
npm install

# 微信小程序（产物：dist/dev/mp-weixin，用微信开发者工具打开）
npm run dev:mp-weixin

# H5 浏览器联调
npm run dev:h5
```

### 环境变量

复制 `.env.example` 为 `.env.local`（不提交 Git）：

| 变量                                | 用途                                                                               |
| ----------------------------------- | ---------------------------------------------------------------------------------- |
| `VITE_MP_WEIXIN_APPID`              | 开发时注入 `src/manifest.json` 的 mp-weixin appid（`vite.config.js` 构建期 patch） |
| `VITE_DEV_OPENID`                   | H5 自动 `dev-login` 的测试 openid                                                  |
| `VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID` | 订阅消息模板 ID（与后端一致）                                                      |
| `VITE_API_*` / `VITE_WS_URL`        | 写入 Vite `define`，**当前 HTTP/WS 默认地址以 `src/config/api.js` 为准**           |

联调前请修改 `src/config/api.js` 中的 `API_BASE_URL`、`WS_BASE_URL`。设置页可覆盖 WebSocket 地址（持久化到 `voice_ws_url`）。

## 目录结构

源码在 `src/` 下，构建入口为根目录 `index.html` → `src/main.js`。

```
frontend/
├── src/
│   ├── pages/                    # 业务页面
│   │   ├── index/                # 首页：月历 + 当日事件
│   │   ├── year-view/            # 年视图
│   │   ├── day-events/           # 某日全部事件
│   │   ├── event-detail/         # 事件详情 / 编辑
│   │   └── settings/             # 设置、权限、WS 地址
│   ├── components/
│   │   ├── CalendarView/         # 月历主视图
│   │   ├── CalendarMonthGrid/    # 月格子
│   │   ├── MiniMonthCard/        # 迷你月卡
│   │   ├── EventList/            # 当日事件列表（首页最多 3 条）
│   │   ├── EventItemsList/       # 完整列表项
│   │   ├── EventSwipeItem/       # 左滑操作
│   │   ├── EventFormModal/       # 新建/编辑表单
│   │   ├── DateTimePicker/       # 日期时间选择
│   │   ├── ConfirmDialog/        # 删除/语音确认弹窗
│   │   ├── GlobalVoice/          # 全局语音入口（麦克风 + 层 + 确认）
│   │   ├── RecordButton/         # 底部对话按钮
│   │   ├── VoiceInteractionLayer/# 会话遮罩
│   │   └── VoiceStatus/          # 状态与文案展示
│   ├── composables/
│   │   ├── useVoiceInteraction.js # 语音会话状态机（核心）
│   │   ├── useVoiceWsClient.js    # WS 协议 + TTS 播放编排
│   │   ├── useVoiceRecorder.js    # 录音（小程序 PCM / H5 Worklet）
│   │   ├── useMpSafeArea.js       # 安全区与底部留白
│   │   ├── usePageSlideNav.js     # 页面滑动导航
│   │   └── useEventListModals.js  # 列表页弹窗逻辑
│   ├── store/modules/
│   │   ├── user.js               # 登录与 Token
│   │   ├── calendar.js           # 日程列表与 CRUD
│   │   ├── voice.js              # 语音 UI 状态
│   │   ├── websocket.js          # WS 连接
│   │   └── confirm.js            # 确认弹窗
│   ├── api/                      # REST 封装
│   ├── config/api.js             # API / WS 基址
│   ├── utils/                    # 日期、音频、映射、登录等
│   ├── types/definitions.js      # JSDoc 类型约定
│   ├── App.vue                   # 启动：健康检查、登录、拉日程
│   ├── pages.json
│   └── manifest.json
├── vite.config.js
├── package.json
└── .env.example
```

`components/FloatingMic/` 等为模板遗留组件，**当前产品未使用**。

## 页面与路由

`src/pages.json` 中已注册页面（均为自定义导航栏，除设置页外）：

| 路径                              | 说明                                          |
| --------------------------------- | --------------------------------------------- |
| `pages/index/index`               | 月历、当日事件摘要、手动新建、`GlobalVoice`   |
| `pages/year-view/year-view`       | 全年缩略月历                                  |
| `pages/day-events/day-events`     | 选中日期下的全部事件                          |
| `pages/event-detail/event-detail` | 查看 / 编辑 / 删除单条事件                    |
| `pages/settings/settings`         | 麦克风、订阅消息、H5 dev-login、WS 地址、引导 |

首页在语音会话激活时会 `disabled` 日历与列表，避免与遮罩层手势冲突。

## 应用启动流程

`App.vue` `onLaunch`：

1. `userStore.restoreFromCache()` — 读取 `wechat_login_info`
2. `checkHealth()` — `GET /api/health`
3. `userStore.ensureAuth()` — 小程序 `wechat-login` / H5 `dev-login`
4. `calendarStore.fetchEvents()` — `GET /api/events`

## 认证

| 平台       | 流程                                                                 | 存储                                   |
| ---------- | -------------------------------------------------------------------- | -------------------------------------- |
| 微信小程序 | `uni.login` → `POST /api/auth/wechat-login`                          | `uni.storage` key: `wechat_login_info` |
| H5         | `POST /api/auth/dev-login`（openid 来自 `VITE_DEV_OPENID` 或设置页） | 同上                                   |

HTTP：`utils/request.js` 自动附加 `Authorization: Bearer <token>`。  
WebSocket：`/ws/voice?token=<jwt>`（`store/modules/websocket.js`）。

## HTTP API 层

| 文件            | 接口                         |
| --------------- | ---------------------------- |
| `api/auth.js`   | `wechat-login`、`dev-login`  |
| `api/events.js` | 日程 CRUD `/events`          |
| `api/health.js` | 健康检查                     |
| `api/wechat.js` | 订阅消息相关                 |
| `api/agent.js`  | 文本 Agent（调试，非主路径） |

响应约定：`{ code: 0, data, message }`，`request.js` 解包 `data`；登录接口返回 `{ token, user }`。

日程字段经 `utils/event-mapper.js` 规范化，与后端 `EventCreate` / `EventUpdate` 对齐；排序见 `utils/event-sort.js`。

## 语音交互架构

### 组件关系

```
GlobalVoice
├── RecordButton          # 点击：开始对话 / 说完了 / 结束对话
├── VoiceInteractionLayer
│   └── VoiceStatus       # 聆听、思考、播报、确认提示
└── ConfirmDialog         # need_confirm 时展示（会话内）
```

`index`、`settings` 等页面引入 `<GlobalVoice />`；非语音场景下的删除确认使用页面级 `ConfirmDialog`。

### 状态机

Pinia `voice` 模块状态（`VOICE_STATUS`）：

```
idle → recording → thinking → speaking → auto_listening → idle
```

| 状态             | 含义                                |
| ---------------- | ----------------------------------- |
| `idle`           | 未开会话                            |
| `recording`      | 用户首轮说话                        |
| `thinking`       | 已发送 audio.end / text，等待 Agent |
| `speaking`       | 播放 TTS 分片                       |
| `auto_listening` | Agent 播完后自动开麦（多轮续聊）    |

### 交互方式（`RecordButton` + `useVoiceInteraction`）

- **空闲**：点击麦克风 → `startSession()`，连接 WS、开录音
- **录音 / 自动聆听**：点击「说完了」→ `finishRecordingAndSend()`，发送 `audio.end`
- **其他会话中状态**：点击「结束对话」→ `exitToIdle()`，断开 WS、停 TTS

静音检测（约 3s 无有效人声）自动结束本轮；最长录音 15s。说出「退出 / 关闭 / 结束」会结束会话。

### WebSocket 协议

与后端及 `backend/tests/frontend/voice_ws_test.html` 对齐。

**客户端 → 服务端**

| type           | 说明                                            |
| -------------- | ----------------------------------------------- |
| `audio_start`  | `session_id`, `format: pcm_s16le`, `sampleRate` |
| `audio.chunk`  | `data`: base64 PCM                              |
| `audio.end`    | 结束本轮音频                                    |
| `text.message` | 文本轮次（确认「确认/取消」、无声音提示等）     |

**服务端 → 客户端**

| type            | 说明                       |
| --------------- | -------------------------- |
| `transcription` | ASR 文本 → 更新 `userText` |
| `agent.reply`   | `text`, `need_confirm`     |
| `tts.chunk`     | base64 PCM，24kHz          |
| `turn.done`     | 本轮结束                   |
| `error`         | 错误信息                   |

实现：`composables/useVoiceWsClient.js` + `utils/voice-tts-player.js`（流式缓冲，H5 用 Web Audio，小程序用 `InnerAudioContext` + WAV 拼接）。

### 录音差异

| 平台       | 实现                                                          |
| ---------- | ------------------------------------------------------------- |
| 微信小程序 | `RecorderManager`，帧回调 + 停止后整段 PCM 分块上传           |
| H5         | `getUserMedia` + `AudioWorklet`，200ms 合并分片 `audio.chunk` |

音频工具：`utils/audio.js`（PCM 检测、base64、WAV 封装等）。

### 轮次策略（`utils/voice-turn-mode.js`）

`turn.done` 且成功后，前端根据 `replyText` 推断模式（**不依赖后端 `turn_mode` 字段**）：

| 模式         | 条件（简述）     | 行为                                  |
| ------------ | ---------------- | ------------------------------------- |
| `write_done` | 增删改完成类话术 | TTS 播完后自动 `exitToIdle`，刷新日程 |
| `query`      | 查询类话术       | 进入 `queryListenMode`，5s 无声音退出 |
| `continue`   | 含问号、需确认等 | TTS 播完后 `auto_listening` 继续开麦  |

`need_confirm` 时展示 `ConfirmDialog`，用户点确认/取消会通过 `text.message` 发送「确认」「取消」。

每轮结束后 `calendarStore.syncAfterVoiceTurn()` 重新拉取日程列表。

## Pinia 模块摘要

| 模块        | 职责                                                      |
| ----------- | --------------------------------------------------------- |
| `user`      | Token、openid、登录去重 `ensureAuth`                      |
| `calendar`  | `events`、`currentDate`、视图年月、`fetchEvents` / 增删改 |
| `voice`     | 会话开关、状态、ASR/回复文案、`needConfirm`               |
| `websocket` | 连接、发送 JSON、`serverUrl` 可配置                       |
| `confirm`   | 全局确认弹窗状态                                          |

## 日历与工具

| 工具                             | 作用             |
| -------------------------------- | ---------------- |
| `utils/date.js`                  | 日期格式化       |
| `utils/calendar-days.js`         | 月历格子数据     |
| `utils/lunar.js` / `holidays.js` | 农历、节假日展示 |
| `utils/mp-subscribe-message.js`  | 微信订阅消息授权 |
| `utils/mp-safe-area.js`          | 安全区           |

## 构建说明

- `npm run build:mp-weixin` / `build:h5` — 生产构建
- `vite.config.js`：注入微信 appid；构建后移除无效的 `scope.record` permission 项（避免开发者工具告警）
- 路径别名：`@` → `src/`（uni 默认）

## 联调建议

1. 后端非 production 环境启动，保证 `API_BASE_URL` / `WS_BASE_URL` 可达
2. 微信小程序：配置合法 appid、录音权限；真机调试语音
3. H5：HTTPS 下测试麦克风；设置页或 `.env.local` 配置 `dev-login` openid
4. 可先使用后端 `tests/frontend/voice_ws_test.html` 单独验证 WS，再对接小程序
