# 声历 Agent 项目开发说明

## 项目目标

本项目是一个基于 AgentScope Runtime 的流式语音日历管理工具。

核心链路：

用户语音 → WebSocket → ASR → Calendar Agent → Tool Calling → Calendar Service → TTS → 前端播放

## 初期开发目标

只做 MVP，不做复杂业务。

优先实现：

1. FastAPI 项目骨架
2. 一个核心 WebSocket 接口 `/ws/voice`
3. 文本调试接口 `/api/agent/text`
4. 本地日历 CRUD
5. Calendar Agent
6. Calendar Tools
7. 后续接入 ASR / TTS

## 技术栈

- Python 3.11
- FastAPI
- WebSocket
- AgentScope Runtime
- DeepSeek V4
- PostgreSQL
- Redis
- Docker Compose

## 代码要求

- 使用异步 FastAPI
- 使用 Pydantic 定义 Schema
- 所有接口返回统一格式
- 工具调用输入输出必须是 JSON
- 初期使用默认用户 `demo_user`
- 先跑通文本链路，再接语音链路
- 每完成一个模块都要写最小测试
