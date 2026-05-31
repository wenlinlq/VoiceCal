语音日历工具 - 前端开发文档 (JavaScript版本)
文档信息
项目 内容
项目名称 语音日历工具（前端）
技术栈 uni-app + Vue3 + Pinia + WebSocket
目标平台 微信小程序
开发周期 3天
文档版本 v1.0
一、项目概述
1.1 产品定位
一个以语音交互为核心的日历管理工具，用户通过说话即可完成日程的添加、查看、删除、修改，比传统手动输入快3倍以上。

1.2 核心能力
能力 说明
语音添加 "明天下午3点开会" → 自动解析并添加
语音查看 "今天有什么安排" → 语音播报 + 列表展示
语音删除 "删除今天下午3点的会" → 确认后删除
语音修改 "把明天的会改到后天" → 智能修改
实时反馈 ASR实时显示识别文字，TTS语音播报结果
1.3 与后端交互方式
通信方式 用途 数据格式
WebSocket 实时音频流收发、状态同步 二进制PCM + JSON
HTTP 初始数据加载、历史查询 JSON
二、技术架构
2.1 技术栈总览
分类 技术 版本 用途
框架 uni-app - 跨端开发
语言 JavaScript ES6+ 主要开发语言
状态管理 Pinia - 状态管理
UI组件 uni-ui - 界面组件
网络 WebSocket API 原生 实时通信
音频采集 RecorderManager 原生 录音
音频播放 InnerAudioContext 原生 TTS播放
构建工具 Vite - 打包构建
2.2 目录结构
javascript
frontend/
├── pages/ // 页面目录
│ ├── index/ // 首页（日历主页）
│ │ ├── index.vue
│ │ └── index.scss
│ ├── event-detail/ // 事件详情页
│ │ └── event-detail.vue
│ └── settings/ // 设置页
│ └── settings.vue
│
├── components/ // 公共组件
│ ├── RecordButton/ // 录音按钮组件
│ │ ├── RecordButton.vue
│ │ └── RecordButton.scss
│ ├── CalendarView/ // 日历视图组件
│ │ ├── CalendarView.vue
│ │ └── CalendarView.scss
│ ├── EventList/ // 事件列表组件
│ │ ├── EventList.vue
│ │ └── EventList.scss
│ ├── ConfirmDialog/ // 确认弹窗组件
│ │ └── ConfirmDialog.vue
│ ├── VoiceStatus/ // 语音状态指示器
│ │ └── VoiceStatus.vue
│ └── FloatingMic/ // 悬浮麦克风（全局）
│ └── FloatingMic.vue
│
├── composables/ // 组合式函数
│ ├── useWebSocket.js // WebSocket管理
│ ├── useRecorder.js // 录音管理
│ ├── useAudioPlayer.js // 音频播放管理
│ └── useCalendar.js // 日历数据管理
│
├── store/ // Pinia状态管理
│ ├── index.js // Store入口
│ └── modules/
│ ├── voice.js // 语音状态模块
│ ├── calendar.js // 日程数据模块
│ ├── websocket.js // WebSocket状态模块
│ └── confirm.js // 确认弹窗模块
│
├── utils/ // 工具函数
│ ├── platform.js // 平台判断工具
│ ├── audio.js // 音频处理工具（PCM转换）
│ ├── date.js // 日期处理工具
│ ├── storage.js // 本地存储封装
│ ├── validator.js // 消息/数据校验工具
│ └── permission.js // 权限引导工具
│
├── types/ // 类型定义（JS版用JSDoc注释）
│ └── definitions.js // 类型定义文件
│
├── static/ // 静态资源
│ └── audio/
│ ├── start.mp3 // 开始录音提示音
│ └── end.mp3 // 结束录音提示音
│
├── App.vue // 应用入口
├── main.js // 主入口文件
├── pages.json // 页面路由配置
├── manifest.json // 应用配置（权限）
├── uni.scss // 全局样式变量
└── package.json // 依赖配置
2.3 页面路由配置（pages.json）
json
{
"pages": [
{
"path": "pages/index/index",
"style": {
"navigationBarTitleText": "语音日历",
"navigationBarBackgroundColor": "#667eea",
"navigationBarTextStyle": "white"
}
},
{
"path": "pages/event-detail/event-detail",
"style": {
"navigationBarTitleText": "事件详情",
"navigationBarBackgroundColor": "#667eea",
"navigationBarTextStyle": "white"
}
},
{
"path": "pages/settings/settings",
"style": {
"navigationBarTitleText": "设置",
"navigationBarBackgroundColor": "#667eea",
"navigationBarTextStyle": "white"
}
}
],
"globalStyle": {
"navigationBarTextStyle": "white",
"navigationBarTitleText": "语音日历",
"navigationBarBackgroundColor": "#667eea",
"backgroundColor": "#f5f7fa"
}
}
三、核心功能模块
3.1 录音按钮组件（RecordButton）
功能描述： 全局悬浮的录音按钮，用户长按开始录音，松手结束并发送。

交互方式：

长按：开始录音（震动反馈 + 提示音）

松手：停止录音并发送

录音中：波动动画 + "录音中..."文字

状态：

状态 样式 文字
空闲 紫色渐变，静态 🎤 长按说话
录音中 红色渐变，波动动画 ⏹️ 松手结束
处理中 灰色，loading动画 ⏳ 处理中
Props：

参数 类型 默认值 说明
disabled Boolean false 是否禁用
position String bottom 位置：bottom / right
3.2 日历视图组件（CalendarView）
功能描述： 展示月/周日历，标记有事件的日期，支持点击日期切换。

功能点：

月份切换（上一月/下一月）

日期点击事件

事件标记点（有事件的日期显示小圆点）

今日高亮

空状态展示：当前月份无日程时显示空提示

Props：

参数 类型 说明
events Array 事件列表
currentDate String 当前选中日期
Events：

事件 参数 说明
dateChange date 日期切换
dateClick date 日期点击
3.3 事件列表组件（EventList）
功能描述： 展示指定日期的事件列表，支持点击进入详情。

显示内容：

事件标题

开始时间 - 结束时间

重复标识（如果有）

空状态展示：当日无日程时显示空提示

3.4 确认弹窗组件（ConfirmDialog）
功能描述： 当后端返回 need_confirm 时弹窗，让用户确认或取消操作。

显示内容：

确认文案（如"确认删除这个会议吗？"）

事件详情（标题、时间）

确认/取消按钮

3.5 语音状态指示器（VoiceStatus）
功能描述： 实时显示当前语音交互状态，让用户知道系统在做什么。

状态映射：

后端状态 前端显示文字 图标
listening 识别中... 🎤 波动
thinking 思考中... 🤔 转圈
speaking 播报中... 🔊 声波
waiting_confirm 请确认 ✋ 弹窗
3.6 悬浮麦克风（FloatingMic）
功能描述： 全局悬浮组件，在需要语音的页面固定显示，位置固定在右下角。

特点：

跨页面固定位置

自动适配安全区域（避开刘海/底部黑条）

可配置显示/隐藏

四、状态管理设计（Pinia - JavaScript版本）
4.1 语音状态模块（voice.js）
javascript
// store/modules/voice.js
import { defineStore } from 'pinia'

export const useVoiceStore = defineStore('voice', {
state: () => ({
status: 'idle', // idle, recording, processing, speaking, waiting_confirm
asrText: '', // 当前ASR识别文字
asrTempText: '' // 临时识别文字（实时显示）
}),

actions: {
setStatus(status) {
this.status = status
},

    setAsrText(text, isFinal) {
      if (isFinal) {
        this.asrText = text
        this.asrTempText = ''
      } else {
        this.asrTempText = text
      }
    },

    reset() {
      this.status = 'idle'
      this.asrText = ''
      this.asrTempText = ''
    }

}
})
4.2 日程数据模块（calendar.js）
javascript
// store/modules/calendar.js
import { defineStore } from 'pinia'

export const useCalendarStore = defineStore('calendar', {
state: () => ({
events: [], // 事件列表
currentDate: '', // 当前选中日期（YYYY-MM-DD）
todayEvents: [] // 今日事件
}),

actions: {
async fetchEvents(date) {
// 获取事件列表
// API调用实现
},

    async addEvent(event) {
      // 添加事件
    },

    async deleteEvent(id) {
      // 删除事件
    },

    async updateEvent(event) {
      // 更新事件
    }

}
})
4.3 WebSocket状态模块（websocket.js）
javascript
// store/modules/websocket.js
import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
state: () => ({
connected: false, // 连接状态
reconnecting: false, // 重连中
reconnectCount: 0 // 重连次数
}),

actions: {
connect() {
// 建立连接
},

    disconnect() {
      // 断开连接
    },

    sendAudio(data) {
      // 发送音频数据
    },

    sendControl(action, data) {
      // 发送控制消息
    }

}
})
4.4 确认弹窗模块（confirm.js）
javascript
// store/modules/confirm.js
import { defineStore } from 'pinia'

export const useConfirmStore = defineStore('confirm', {
state: () => ({
visible: false, // 弹窗是否显示
event: null, // 待确认的事件
message: '' // 确认文案
}),

actions: {
showConfirm(event, message) {
this.event = event
this.message = message
this.visible = true
},

    hideConfirm() {
      this.visible = false
      this.event = null
      this.message = ''
    },

    confirm() {
      // 确认操作
      this.hideConfirm()
    },

    cancel() {
      // 取消操作
      this.hideConfirm()
    }

}
})
五、WebSocket通信协议
5.1 连接地址
text
ws://{BACKEND_HOST}:8080/ws/voice
5.2 前端发送消息格式
音频数据（二进制）： 直接发送 PCM 音频分片（每片 500ms-1s）

补充规则： 二进制PCM与JSON控制消息混传，统一增加4字节消息头区分消息类型，防止粘包、解析错乱；消息头标识：0x01=音频流、0x02=JSON控制消息。

控制消息（JSON）：

action 说明 示例
start 开始录音 {"type":"control","action":"start"}
stop 停止录音 {"type":"control","action":"stop"}
confirm 确认操作 {"type":"control","action":"confirm"}
cancel 取消操作 {"type":"control","action":"cancel"}
heartbeat 心跳包 {"type":"control","action":"heartbeat"}
5.3 后端发送消息格式
type 说明 示例
asr ASR识别结果 {"type":"asr","is_final":false,"text":"明天"}
status Agent状态 {"type":"status","state":"thinking"}
need_confirm 需要确认 {"type":"need_confirm","event":{},"message":"确认删除吗？"}
tts TTS音频 {"type":"tts","audio":"base64..."}
result 操作结果 {"type":"result","success":true,"message":"已添加"}
补充规则： 前端接收后端消息后，统一做字段、类型校验，异常消息直接丢弃并打印日志，避免页面报错。

5.4 状态流转
text
null → connecting → connected → idle
│
┌─────────┼─────────┐
▼ ▼ ▼
recording speaking waiting_confirm
│ │ │
└─────────┴─────────┘
│
▼
idle
5.5 心跳与重连机制（新增）
心跳间隔：前端每 25s 主动发送 heartbeat 心跳包，维持长连接

超时判定：连续2次未收到后端响应，判定为连接断开

重连策略：最大重连次数 8 次，重连间隔阶梯递增（1s/2s/4s/8s）

页面状态联动：APP/小程序前后台切换、页面切走时，主动断开连接；切回前台自动触发重连

断连兜底：连接断开时强制停止录音、释放麦克风、清空ASR文本、重置语音状态

六、录音模块实现要点
6.1 跨端录音方案
平台 API 配置要点
微信小程序 wx.getRecorderManager format: 'pcm', sampleRate: 16000, numberOfChannels: 1
App uni.getRecorderManager 同上
H5 navigator.mediaDevices.getUserMedia 需要 AudioContext 处理
补充约束： H5 环境仅支持 HTTPS/WSS 协议，HTTP 域名下浏览器会禁用麦克风权限，线上环境必须部署HTTPS。

6.2 音频参数（必须与后端对齐）
参数 值
采样率 16000 Hz
声道 单声道
位深 16 bit
格式 PCM
分片大小 500ms ~ 1000ms
补充规则： 增加分片容错逻辑，过滤空分片、异常大小分片，超时未发送的分片直接丢弃。

6.3 录音流程
text

1. 请求麦克风权限
2. 配置录音参数（16kHz/单声道/PCM）
3. 开始录音
4. 定时器每500ms获取音频数据
5. 通过WebSocket发送音频分片
6. 停止录音
7. 发送stop控制消息
   新增边界处理：

页面锁屏、来电、切页、APP后台运行时，自动终止录音

麦克风权限被拒绝时，调用权限引导工具，提示用户前往系统设置开启权限

七、音频播放模块实现要点
7.1 TTS音频播放
平台 API 说明
微信小程序 wx.createInnerAudioContext 支持 base64 或 网络音频
App uni.createInnerAudioContext 同上
H5 AudioContext 需要处理 PCM 数据
7.2 播放队列
javascript
// composables/useAudioPlayer.js
class AudioPlayerQueue {
constructor() {
this.queue = [] // 音频base64队列
this.isPlaying = false
this.audioContext = null
}

add(audioBase64) {
this.queue.push(audioBase64)
if (!this.isPlaying) {
this.play()
}
}

play() {
// 播放队列
}

onEnd() {
// 播放完成，播下一个
}

clear() {
this.queue = []
this.isPlaying = false
}
}
八、页面详细设计
8.1 首页（index）
布局结构：

text
┌─────────────────────────────────────┐
│ ← 2026年5月 → │
├─────────────────────────────────────┤
│ 一 二 三 四 五 六 日 │
│ 26 27 28 29 30 31 1 │
│ 2 3 4 5 6 7 8 │
│ ● ● │
├─────────────────────────────────────┤
│ 📋 今日事件 更多 >│
├─────────────────────────────────────┤
│ 🕐 15:00 产品评审会 │
│ 🕐 17:00 周报提交 │
│ 🕐 19:00 健身 │
├─────────────────────────────────────┤
│ │
│ ┌─────────────┐ │
│ │ 🎤 │ │
│ │ 长按说话 │ │
│ └─────────────┘ │
└─────────────────────────────────────┘
页面状态：

状态 日历区域 列表区域 麦克风
空闲 可交互 显示事件 待机
录音中 禁用 禁用 波动动画
处理中 禁用 禁用 loading
播报中 可交互 可交互 待机
补充优化：

日历日期切换、ASR实时文本渲染增加防抖处理，降低页面重绘频率

全局页面、日历组件、列表组件全量适配刘海屏、底部安全区

网络请求失败、WebSocket连接失败时，展示错误提示+重试按钮

8.2 事件详情页（event-detail）
布局结构：

text
┌─────────────────────────────────────┐
│ ← 返回 编辑 删除 │
├─────────────────────────────────────┤
│ │
│ 📅 产品评审会 │
│ │
│ ┌─────────────────────────────┐ │
│ │ 🕐 时间 15:00 - 16:00 │ │
│ │ 📅 日期 2026年5月29日 │ │
│ │ 🔁 重复 不重复 │ │
│ │ 📝 备注 腾讯会议 123456 │ │
│ └─────────────────────────────┘ │
│ │
│ ┌─────────────┐ │
│ │ 🎤 修改事件 │ │
│ └─────────────┘ │
└─────────────────────────────────────┘
8.3 设置页（settings）
功能 说明
麦克风权限 检查/申请权限
清除缓存 清除本地存储的日程缓存
WebSocket服务器 配置后端地址（开发用）
使用引导 语音指令示例
关于 版本信息
九、开发环境配置
9.1 环境变量
bash

# .env.development

VITE_WS_URL = "ws://localhost:8080/ws/voice"
VITE_API_URL = "http://localhost:8080/api"

# .env.production

VITE_WS_URL = "wss://shturl.cc/iaJBml67kjkfNi"
VITE_API_URL = "shturl.cc/gIvr6sRduXRczZGCE"
9.2 manifest.json 权限配置
json
{
"name": "语音日历",
"appid": "**UNI**XXXXXX",
"mp-weixin": {
"appid": "your_wechat_appid",
"permission": {
"scope.record": {
"desc": "用于语音添加日历事件"
}
},
"requiredPrivateInfos": ["getRecorderManager"]
},
"app-plus": {
"distribute": {
"ios": {
"plistcmds": [
"Add :NSMicrophoneUsageDescription string 用于语音添加日历事件"
]
},
"android": {
"permissions": [
"android.permission.RECORD_AUDIO"
]
}
}
}
}
9.3 package.json 依赖
json
{
"name": "voice-calendar",
"version": "1.0.0",
"scripts": {
"dev:mp-weixin": "uni -p mp-weixin",
"dev:h5": "uni",
"build:mp-weixin": "uni build -p mp-weixin",
"build:h5": "uni build"
},
"dependencies": {
"@dcloudio/uni-app": "^3.0.0",
"@dcloudio/uni-app-plus": "^3.0.0",
"@dcloudio/uni-components": "^3.0.0",
"@dcloudio/uni-h5": "^3.0.0",
"@dcloudio/uni-mp-weixin": "^3.0.0",
"pinia": "^2.1.0",
"vue": "^3.3.0"
},
"devDependencies": {
"@dcloudio/types": "^3.3.0",
"@dcloudio/vite-plugin-uni": "^3.0.0",
"vite": "^4.0.0"
}
}
十、开发进度安排（3天）
天数 任务 产出
Day1 项目初始化、WebSocket模块、录音模块 WebSocket可连接、录音可发送PCM
Day1 首页框架、日历组件基础 日历可展示、可点击
Day2 接收ASR/TTS、音频播放队列 实时显示识别文字、可播放语音
Day2 状态管理、事件列表 状态同步、事件增删改查
Day3 确认弹窗、悬浮麦克风、跨端适配 完整交互闭环
Day3 样式打磨、性能优化、联调测试 可演示的MVP
十一、与后端接口对齐清单
在开发前，需要和后端确认以下内容：

确认项 状态 说明
WebSocket地址 ⬜ ws://ip:8080/ws/voice
PCM音频参数 ⬜ 16kHz / 单声道 / 16bit
状态码枚举 ⬜ listening/thinking/speaking/waiting_confirm
need_confirm数据结构 ⬜ event对象字段
TTS音频格式 ⬜ base64 MP3 还是 PCM
心跳机制 ⬜ 是否需要前端发心跳、心跳间隔
十二、风险与注意事项
风险 影响 缓解措施
小程序PCM格式支持 高 优先验证录音格式是否符合后端要求
WebSocket断线 中 实现自动重连 + 心跳保活
音频播放队列乱序 中 实现队列管理，确保顺序播放
跨端录音差异 中 封装平台适配层，逐个测试
权限被拒绝 低 友好的权限引导提示
H5协议限制 高 线上环境强制使用HTTPS/WSS协议
消息粘包解析异常 中 统一增加消息头区分二进制/JSON数据
低端机型动画卡顿 中 录音波动、loading动画开启CSS硬件加速，减少重绘
弱网离线体验 中 日程数据优先读取本地Storage缓存，HTTP做增量更新
十三、附录
附录A：JavaScript类型定义（使用JSDoc注释）
javascript
// types/definitions.js

/\*\*

- @typedef {Object} Event
- @property {number} [id] - 事件ID
- @property {string} title - 事件标题
- @property {string} start_time - 开始时间 (YYYY-MM-DD HH:MM:SS)
- @property {string} [end_time] - 结束时间
- @property {'none'|'daily'|'weekly'|'monthly'} repeat_type - 重复类型
- @property {string} [created_at] - 创建时间
  \*/

/\*\*

- @typedef {('idle'|'recording'|'processing'|'speaking'|'waiting_confirm')} WSStatus
  \*/

/\*\*

- @typedef {('listening'|'thinking'|'speaking'|'waiting_confirm')} AgentState
  \*/

/\*\*

- @typedef {Object} ASRMessage
- @property {'asr'} type
- @property {boolean} is_final
- @property {string} text
  \*/

/\*\*

- @typedef {Object} StatusMessage
- @property {'status'} type
- @property {AgentState} state
  \*/

/\*\*

- @typedef {Object} NeedConfirmMessage
- @property {'need_confirm'} type
- @property {Event} event
- @property {string} message
  \*/

/\*\*

- @typedef {Object} TTSMessage
- @property {'tts'} type
- @property {string} audio - base64编码的音频数据
  \*/

/\*\*

- @typedef {Object} ResultMessage
- @property {'result'} type
- @property {boolean} success
- @property {string} message
  \*/

/\*\*

- @typedef {Object} HeartBeatMessage
- @property {'control'} type
- @property {'heartbeat'} action
  \*/
