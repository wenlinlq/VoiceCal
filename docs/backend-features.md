# 声历 VoiceCal Backend 功能清单

## 一、API 接口

### 1.1 健康检查
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 服务健康检查，返回 `{"status": "running"}` |

### 1.2 用户认证
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/wechat-login` | POST | 微信小程序登录，用 `wx.login()` 返回的 code 换取 JWT token |
| `/api/auth/dev-login` | POST | 开发环境快捷登录（非 production 可用），传 openid 直接返回 JWT |
| `/api/auth/refresh` | POST | 刷新 JWT token |

**特性**：
- JWT 签发与验证（`app/core/auth.py`）
- 微信 code → openid 换取（调微信 `jscode2session`）
- 开发环境跳过微信校验
- 用户自动创建/查询（`user_service.py`）

### 1.3 日程管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/events` | GET | 查询日程列表，支持 `start`/`end` 时间范围和 `keyword` 模糊搜索 |
| `/api/events` | POST | 创建日程 |
| `/api/events/{id}` | GET | 查询单个日程 |
| `/api/events/{id}` | PUT | 更新日程 |
| `/api/events/{id}` | DELETE | 删除日程 |

**特性**：
- 所有操作按 `user_id` 隔离（JWT 鉴权）
- 时间范围查询 + 关键词模糊搜索（标题、描述）
- 日程完成状态标记
- 提醒字段：`remind_at`, `remind_enabled`, `push_status`, `subscribe_template_id`

### 1.4 语音 WebSocket
| 接口 | 方法 | 说明 |
|------|------|------|
| `/ws/voice?token=JWT` | WebSocket | 全双工语音交互通道 |

**消息协议**：

客户端 → 服务端：
- `text.message` — 文本消息（调试或确认回复）
- `audio.start` / `audio.chunk` / `audio.end` — PCM 音频流（16kHz 16bit mono）

服务端 → 客户端：
- `transcription` — ASR 转录结果
- `agent.reply` — Agent 文本回复（含 `need_confirm` 标记）
- `tts.chunk` — TTS 音频分片（base64 PCM，含 `is_last` 标记）
- `turn.done` — 本轮交互结束
- `error` — 错误消息

### 1.5 微信订阅消息
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/wechat/subscribe-result` | POST | 保存用户订阅授权结果（`accept` / `reject` / `ban`） |

---

## 二、AI 能力

### 2.1 Skill Router（意图分流）
- 文件：`app/services/skill_router.py`
- 功能：在 ReActAgent 之前做意图分类 + 实体提取
- 常见操作（创建、查询、删除）走快速通道：**1 次 LLM 调用 + 直接工具执行**
- 复杂操作（修改、闲聊、低置信度）降级给 ReActAgent
- LLM 结构化输出（`CalendarIntent` Pydantic 模型）
- 支持确认词/取消词快速检测（不走 LLM）
- 3 秒超时保护，失败自动降级

### 2.2 ReActAgent（AgentScope Runtime）
- 文件：`app/services/agent_service.py`
- 模型：Qwen-Plus（可配置）
- 工具注册：`get_current_time`, `parse_datetime`, `query_calendar_events`, `check_time_conflict`, `detect_duplicate_events`, `suggest_available_slots`, `add_calendar_event`, `delete_calendar_event`, `update_calendar_event`, `get_event_by_id`, `create_reminder`
- 确认机制：写操作首次不带 `confirm`，工具返回 `CONFIRM_REQUIRED`，用户确认后重试
- 兜底机制：Agent 失败时，用关键词匹配 + 直接工具调用补充
- 长期记忆集成：Mem0 + Milvus 向量检索
- TTS 模式：`tts_model=None`，由 WebSocket 层 fallback 服务兜底

### 2.3 自然语言时间解析
- 文件：`app/tools/calendar_tools.py` → `_extract_reference_date`
- 支持模式：
  - 相对日期：今天/明天/后天/大后天/昨天/前天
  - 星期：下周一/本周三/周二/下下周一
  - 数量：X天后/X小时之后/X分钟后/半小时后
  - 绝对日期：6月2号/12月31日/2号/15日
  - ISO 格式：2026-06-02
- 时间提取：`_extract_slots` 提取小时:分钟，支持"早上/上午/中午/下午/晚上/凌晨"
- LLM 直接输出 ISO 8601 格式（prompt 引导）

### 2.4 ASR 语音识别
- 文件：`app/services/asr_service.py`
- 模型：`paraformer-realtime-v2`（DashScope）
- 格式：PCM 16kHz 16bit mono
- 流程：音频分片累积 → `audio.end` → 合成完整 WAV → 调用 Recognition API → 返回文本
- 调试：每次转录自动保存 `/tmp/voicecal_last_asr.wav`

### 2.5 TTS 语音合成
- 文件：`app/services/tts_service.py`
- 模型：`sambert-zhichu-v1`（DashScope SpeechSynthesizer）
- 格式：PCM 24kHz 16bit mono
- 流程：`SpeechSynthesizer.call()` → 回调收集音频帧 → 分片发送前端
- 兜底路径：Agent 无 TTS → WebSocket 层调独立 TTS 服务
- 文字清洗：`_clean_tts_text` 过滤 emoji、Markdown、多余空白

### 2.6 系统 Prompt
- 文件：`app/services/prompts.py`
- 包含：操作规则、确认流程示例、查询示例、反例、语音交互风格

---

## 三、数据与存储

### 3.1 数据库模型
| 模型 | 表 | 说明 |
|------|------|------|
| `Event` | `events` | 日程：title/description/location/start_time/end_time/is_all_day/completed/remind_at/remind_enabled/push_status/pushed_at/subscribe_template_id |
| `UserSubscription` | `user_subscriptions` | 用户订阅授权：user_id/template_id/status |
| `User` | `users` | 用户：openid/nickname/avatar_url |

### 3.2 短期记忆
- 文件：`app/services/memory_manager.py`
- Redis 存储，按 `(user_id, session_id)` 命名空间隔离
- TTL 自动过期
- Redis 不可用时自动降级 InMemoryMemory
- 带日志的 `LoggingMemory` 包装层

### 3.3 长期记忆
- 文件：`app/services/memory_manager.py` → `VoiceCalendarLongTermMemory`
- 引擎：Mem0 + Milvus 向量数据库 + DashScope Embedding
- 两种模式：
  - `static_control`：每次 reply 前后自动检索/记录
  - `agent_control`：Agent 可主动调用 `retrieve_from_memory` / `record_to_memory` 工具
- 所有操作带超时保护（默认 5s），不阻塞 Agent 主流程

### 3.4 Session 管理
- 文件：`app/services/session_service.py`
- Redis 存储 session 状态
- 记录最后交互时间、用户文本、pending action 等

---

## 四、微信集成

### 4.1 推送服务
- 文件：`app/services/wechat_push_service.py`
- Access Token 管理：自动获取 + Redis 缓存 + 提前刷新
- 模板消息发送：`POST /cgi-bin/message/subscribe/send`
- 定时扫描：`scan_and_push_reminders()` 每分钟执行
- 推送状态：`pending` → `sent` / `failed` / `no_auth` / `expired`
- emoji 字段处理：`_strip_emoji` 过滤 `phrase5` 字段
- 模板字段映射：`thing3`(提醒事项) / `phrase5`(事项主题 5字) / `time13`(时间) / `thing4`(地点)

### 4.2 推送调度器
- 文件：`app/services/push_scheduler.py`
- APScheduler 每分钟触发 `scan_and_push_reminders`
- FastAPI lifespan 中启动/关闭

---

## 五、基础设施

### 5.1 配置管理
- 文件：`app/core/config.py`
- 所有配置通过环境变量读取（Pydantic Settings）
- 支持 `.env` 文件
- 关键配置项：
  - `DASHSCOPE_API_KEY` — LLM/ASR/TTS API Key
  - `DATABASE_URL` — PostgreSQL 连接
  - `REDIS_URL` — Redis 连接
  - `WECHAT_APPID` / `WECHAT_SECRET` — 微信小程序
  - `WECHAT_SUBSCRIBE_TEMPLATE_ID` — 订阅消息模板
  - `MEM0_VECTOR_STORE` / `MILVUS_*` — 向量数据库

### 5.2 数据库连接
- 文件：`app/db/database.py`
- SQLAlchemy async + asyncpg
- 自动建表/补列（`sync_schema`）
- Session factory 模式

### 5.3 鉴权
- 文件：`app/core/auth.py`
- JWT 签发/验证
- `get_current_user` 依赖注入
- WebSocket 的 token 从 query param 解析

### 5.4 统一响应
- 文件：`app/core/response.py`
- `APIResponse.success(data)` / `APIResponse.error(message)`

### 5.5 部署
- `Dockerfile`：Python 3.11-slim + pip 清华源
- `docker-compose.yml`：app + PostgreSQL + Redis
- `docker-compose.memory.yml`：Milvus + MinIO + etcd
- 启动命令：`docker compose -f docker-compose.yml -f docker-compose.memory.yml up -d --build`

---

## 六、文件结构总览

```
backend/
├── app/
│   ├── agents/          # Agent 适配层
│   │   └── calendar_agent.py
│   ├── api/             # REST + WebSocket 接口
│   │   ├── agent.py     # /api/agent/text 文本调试
│   │   ├── auth.py      # /api/auth/* 认证
│   │   ├── events.py    # /api/events CRUD
│   │   ├── health.py    # /api/health
│   │   ├── subscribe.py # /api/wechat/subscribe-result
│   │   └── websocket.py # /ws/voice 语音主接口
│   ├── core/            # 基础设施
│   │   ├── auth.py      # JWT 鉴权
│   │   ├── config.py    # 配置管理
│   │   └── response.py  # 统一响应格式
│   ├── db/              # 数据库
│   │   └── database.py
│   ├── models/          # 数据模型
│   │   ├── event.py
│   │   ├── subscription.py
│   │   └── user.py
│   ├── schemas/         # Pydantic Schema
│   │   ├── agent_schema.py
│   │   ├── event_schema.py
│   │   └── ws_schema.py
│   ├── services/        # 服务层
│   │   ├── agent_service.py      # ReActAgent 主服务
│   │   ├── asr_service.py        # ASR 语音识别
│   │   ├── calendar_service.py   # 日程 CRUD
│   │   ├── memory_manager.py     # 短期+长期记忆
│   │   ├── prompts.py            # 系统提示词
│   │   ├── push_scheduler.py     # 推送调度器
│   │   ├── session_service.py    # Session 管理
│   │   ├── skill_router.py       # 意图分流
│   │   ├── tts_service.py        # TTS 语音合成
│   │   ├── user_service.py       # 用户服务
│   │   └── wechat_push_service.py # 微信推送
│   ├── tools/           # Agent 工具
│   │   └── calendar_tools.py
│   └── main.py          # FastAPI 入口 + lifespan
├── tests/               # 测试
│   ├── test_agent.py
│   ├── test_events.py
│   ├── test_memory_manager.py
│   ├── test_subscribe.py
│   ├── test_tts_latency.py
│   ├── test_wechat_push_live.py
│   ├── test_wechat_push_service.py
│   └── test_websocket.py
├── Dockerfile
├── docker-compose.yml
├── docker-compose.memory.yml
├── requirements.txt
└── .env
```
