# 声历 VoiceCal

**AI 语音日程管家 — 用说话管理所有日程**

> 🔗 **体验地址：[https://latekin.jufu.vip](https://latekin.jufu.vip)**

---

## 项目简介

声历是一款基于大语言模型的智能语音日程管理工具。用户通过自然语言与 AI 对话，即可完成日程的创建、查询、修改、删除，并获得定时微信推送提醒。一套代码同时支持微信小程序和 H5 浏览器。

---

## 效果展示

![效果展示](docs/项目功能和流程介绍图.png)

---

## 技术架构

![系统架构](docs/架构图.png)

![组件和技术栈](docs/项目组件和技术栈介绍图.png)

---

## 项目结构

```
VoiceCal/
├── frontend/                    # 前端 uni-app 工程
│   ├── src/
│   │   ├── pages/               # 页面（登录、日历首页、年视图等）
│   │   ├── components/          # 组件（日历、事件列表、语音状态等）
│   │   ├── composables/         # 组合式 API（语音交互、录音、WS 客户端）
│   │   ├── utils/               # 工具（TTS 播放器、订阅消息、音频处理）
│   │   └── store/               # Pinia 状态管理
│   └── dist/                    # 编译产物
│
├── backend/                     # 后端 Python 工程
│   ├── app/
│   │   ├── api/                 # REST + WebSocket 接口
│   │   ├── services/            # 核心服务（Agent、ASR、TTS、记忆、推送）
│   │   ├── tools/               # Agent 工具集
│   │   └── models/              # 数据模型
│   └── tests/                   # pytest 测试
│
├── docs/                        # 项目文档
│   ├── 项目演示介绍.md
│   ├── 演示脚本.md
│   ├── 口播文案.md
│   └── backend-features.md
│
└── README.md
```

---

## 核心特性

- **全链路语音交互** — 说话 → ASR → Agent → TTS → 前端播放，全程免打字
- **Skill Router 分流** — 常见操作 1 次 LLM，复杂操作降级 Agent，快 2-3 倍
- **智能时间解析** — 支持「明天下午三点」「下周二」「6月2号」等自然表达
- **长期记忆** — Mem0 + Milvus，跨会话记住用户偏好
- **微信订阅推送** — 原生授权弹窗，到时间自动推送服务通知
- **多用户隔离** — Redis Session + JWT 鉴权
- **跨平台** — Vue 3 / uni-app → 微信小程序 + H5

---

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Vue 3 / uni-app / Pinia / WebSocket / Canvas |
| 后端 | Python 3.11 / FastAPI / AgentScope Runtime |
| LLM | Qwen-Plus |
| ASR | Paraformer Realtime V2 |
| TTS | Sambert-zhichu V1 |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 向量库 | Milvus 2.5 + Mem0 |
| 部署 | Docker Compose / Nginx / Let's Encrypt |

---

## 本地运行

```bash
# 后端
cd backend
cp .env.example .env   # 编辑填入 API Key
docker compose up -d

# 前端（H5 浏览器）
cd frontend
npm install
npm run dev:h5          # → http://localhost:5173

# 前端（微信小程序）
npm run dev:mp-weixin   # 微信开发者工具导入 dist/dev/mp-weixin
```

## 部署

详见 [backend/README.md](backend/README.md)
