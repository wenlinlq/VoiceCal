import { computed } from 'vue'
import { useVoiceStore, VOICE_STATUS } from '@/store/modules/voice.js'
import { useWebSocketStore } from '@/store/modules/websocket.js'
import { useCalendarStore } from '@/store/modules/calendar.js'
import { useUserStore } from '@/store/modules/user.js'
import { useVoiceRecorder } from '@/composables/useVoiceRecorder.js'
import { DEFAULT_USER_ID } from '@/config/api.js'
import {
  arrayBufferToBase64,
  base64ToArrayBuffer,
  detectSound,
  detectSoundFloat,
  mergeArrayBuffers,
  pcmToWav,
} from '@/utils/audio.js'

const RECORD_SILENCE_MS = 3000
const AUTO_LISTEN_SILENCE_MS = 10000
const MAX_RECORDING_MS = 15000
const CHUNK_SEND_INTERVAL_MS = 200
const EXIT_KEYWORDS = ['退出', '关闭']

/** 模块级单例 */
const voiceRecorder = useVoiceRecorder()
let silenceWatchTimer = null
let ttsBuffers = []
let innerAudio = null
let h5AudioEl = null
let wsHandlerBound = false
let isAutoListenRound = false
let isEnding = false
let hasSpoken = false
let sentChunkCount = 0
let recordingSampleRate = 16000
let recordingStartedAt = 0
let lastSoundAt = 0
let pendingChunkBuffers = []
let lastChunkSendAt = 0

function createSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function getUserId() {
  const userStore = useUserStore()
  return userStore.openid || DEFAULT_USER_ID
}

function stopSilenceWatch() {
  if (silenceWatchTimer) {
    clearInterval(silenceWatchTimer)
    silenceWatchTimer = null
  }
}

function checkExitKeyword(text) {
  if (!text) return false
  return EXIT_KEYWORDS.some((kw) => text.includes(kw))
}

function playTtsPcm(buffers) {
  if (!buffers.length) return
  const pcm = mergeArrayBuffers(buffers)
  const wav = pcmToWav(pcm, 16000)

  // #ifdef H5
  if (!h5AudioEl) h5AudioEl = new Audio()
  if (h5AudioEl._blobUrl) URL.revokeObjectURL(h5AudioEl._blobUrl)
  const blob = new Blob([wav], { type: 'audio/wav' })
  h5AudioEl._blobUrl = URL.createObjectURL(blob)
  h5AudioEl.src = h5AudioEl._blobUrl
  h5AudioEl.play().catch((err) => console.warn('[tts] H5 play fail', err))
  // #endif

  // #ifdef MP-WEIXIN
  if (!innerAudio) {
    innerAudio = uni.createInnerAudioContext()
    innerAudio.onError((err) => console.warn('[tts] play error', err))
  }
  const fs = uni.getFileSystemManager()
  const filePath = `${uni.env.USER_DATA_PATH}/tts_${Date.now()}.wav`
  fs.writeFile({
    filePath,
    data: wav,
    success: () => {
      innerAudio.src = filePath
      innerAudio.play()
    },
    fail: (err) => console.warn('[tts] write file fail', err),
  })
  // #endif
}

function stopTts() {
  // #ifdef H5
  if (h5AudioEl) {
    h5AudioEl.pause()
    if (h5AudioEl._blobUrl) {
      URL.revokeObjectURL(h5AudioEl._blobUrl)
      h5AudioEl._blobUrl = null
    }
  }
  // #endif
  // #ifdef MP-WEIXIN
  if (innerAudio) {
    try {
      innerAudio.stop()
    } catch (_) {}
  }
  // #endif
  ttsBuffers = []
}

function bindWsHandler() {
  if (wsHandlerBound) return
  const wsStore = useWebSocketStore()
  wsStore.setMessageHandler(handleWsMessage)
  wsHandlerBound = true
}

function handleWsMessage(msg) {
  const voiceStore = useVoiceStore()

  switch (msg.type) {
    case 'transcription': {
      const text = msg.text || ''
      voiceStore.setUserText(text)
      if (checkExitKeyword(text)) {
        getVoiceActions().exitToIdle()
      }
      break
    }

    case 'agent.reply':
      voiceStore.setReplyText(msg.text, msg.need_confirm)
      if (
        voiceStore.status === VOICE_STATUS.THINKING ||
        voiceStore.status === VOICE_STATUS.RECORDING
      ) {
        voiceStore.setStatus(VOICE_STATUS.SPEAKING)
      }
      break

    case 'tts.chunk':
      if (voiceStore.status === VOICE_STATUS.THINKING) {
        voiceStore.setStatus(VOICE_STATUS.SPEAKING)
      }
      if (msg.data) {
        ttsBuffers.push(base64ToArrayBuffer(msg.data))
      }
      if (msg.is_last) {
        playTtsPcm(ttsBuffers)
        ttsBuffers = []
      }
      break

    case 'turn.done':
      isEnding = false
      if (msg.success) {
        const calendarStore = useCalendarStore()
        calendarStore.fetchEvents(calendarStore.currentDate).catch(() => {})
      }
      if (voiceStore.sessionOpen && voiceStore.status !== VOICE_STATUS.IDLE) {
        getVoiceActions().enterAutoListening()
      }
      break

    case 'error':
      isEnding = false
      handleServerError(msg.message || '语音处理失败')
      break

    default:
      break
  }
}

function handleServerError(message) {
  const voiceStore = useVoiceStore()
  if (message.includes('empty transcription') || message.includes('empty text')) {
    voiceStore.setError('没有听清，请再来说一次')
  } else {
    voiceStore.setError(message)
  }
  setTimeout(() => {
    if (voiceStore.sessionOpen) {
      getVoiceActions().enterAutoListening()
    }
  }, 1500)
}

let voiceActions = null
function getVoiceActions() {
  return voiceActions
}

export function useVoiceInteraction() {
  const voiceStore = useVoiceStore()
  const wsStore = useWebSocketStore()

  bindWsHandler()

  const showVoiceLayer = computed(() => voiceStore.sessionOpen)
  const isVoiceActive = computed(() => voiceStore.status !== VOICE_STATUS.IDLE)

  async function ensureConnected() {
    if (!wsStore.connected) {
      await wsStore.connect(getUserId())
    }
  }

  function flushPendingChunks() {
    if (!pendingChunkBuffers.length) return
    const merged = mergeArrayBuffers(pendingChunkBuffers)
    pendingChunkBuffers = []
    sentChunkCount += 1
    wsStore.send({
      type: 'audio.chunk',
      session_id: voiceStore.sessionId,
      user_id: getUserId(),
      data: arrayBufferToBase64(merged),
    })
    lastChunkSendAt = Date.now()
  }

  function onAudioFrame(frameBuffer, float32) {
    if (!voiceStore.sessionOpen || isEnding) return

    const sounded = float32
      ? detectSoundFloat(float32)
      : detectSound(frameBuffer)

    if (sounded) {
      hasSpoken = true
      lastSoundAt = Date.now()
    }

    pendingChunkBuffers.push(frameBuffer)
    const now = Date.now()
    if (now - lastChunkSendAt >= CHUNK_SEND_INTERVAL_MS) {
      flushPendingChunks()
    }
  }

  function startSilenceWatch(isAutoListen) {
    stopSilenceWatch()
    recordingStartedAt = Date.now()
    lastSoundAt = recordingStartedAt
    lastChunkSendAt = 0

    silenceWatchTimer = setInterval(() => {
      if (!voiceStore.sessionOpen || isEnding) return

      const status = voiceStore.status
      if (status !== VOICE_STATUS.RECORDING && status !== VOICE_STATUS.AUTO_LISTENING) {
        return
      }

      const now = Date.now()
      const silentFor = now - lastSoundAt
      const totalFor = now - recordingStartedAt

      if (isAutoListen) {
        if (silentFor >= AUTO_LISTEN_SILENCE_MS) {
          getVoiceActions().exitToIdle()
        }
        return
      }

      if (totalFor >= MAX_RECORDING_MS) {
        console.log('[voice] max recording duration reached')
        finishRecordingAndSend()
        return
      }

      if (hasSpoken && silentFor >= RECORD_SILENCE_MS) {
        console.log('[voice] silence after speech, sending audio.end')
        finishRecordingAndSend()
      }
    }, 300)
  }

  function sendAudioStart(rate) {
    wsStore.send({
      type: 'audio_start',
      session_id: voiceStore.sessionId,
      user_id: getUserId(),
      format: 'pcm_s16le',
      sampleRate: rate,
    })
  }

  function finishRecordingAndSend() {
    if (isEnding) return

    flushPendingChunks()

    if (sentChunkCount === 0) {
      voiceStore.setError('未采集到音频，请检查麦克风权限')
      return
    }

    isEnding = true
    stopSilenceWatch()
    voiceRecorder.stop()

    const sent = wsStore.send({
      type: 'audio.end',
      session_id: voiceStore.sessionId,
      user_id: getUserId(),
      sample_rate: recordingSampleRate,
    })

    if (!sent) {
      isEnding = false
      voiceStore.setError('语音连接已断开')
      return
    }

    console.log('[voice] audio.end sent, chunks=', sentChunkCount, 'hasSpoken=', hasSpoken)
    voiceStore.setStatus(VOICE_STATUS.THINKING)
  }

  async function enterRecording(isAuto = false) {
    if (!voiceStore.sessionOpen) return

    isAutoListenRound = isAuto
    isEnding = false
    hasSpoken = false
    sentChunkCount = 0
    pendingChunkBuffers = []
    ttsBuffers = []

    voiceStore.setStatus(isAuto ? VOICE_STATUS.AUTO_LISTENING : VOICE_STATUS.RECORDING)

    if (!isAuto) {
      voiceStore.clearTurn()
    } else {
      voiceStore.errorText = ''
    }

    try {
      await ensureConnected()
      recordingSampleRate = await voiceRecorder.start(onAudioFrame)
      console.log('[voice] recording started, sampleRate=', recordingSampleRate)
      sendAudioStart(recordingSampleRate)
      startSilenceWatch(isAuto)
    } catch (err) {
      console.error('[voice] enterRecording failed', err)
      voiceStore.setError('无法启动录音')
      exitToIdle()
    }
  }

  async function enterAutoListening() {
    if (!voiceStore.sessionOpen) return
    await enterRecording(true)
  }

  async function startSession() {
    try {
      await ensureConnected()
    } catch (err) {
      console.error('[voice] ws connect fail', err)
      uni.showToast({ title: '无法连接语音服务', icon: 'none' })
      return
    }

    voiceStore.openSession()
    voiceStore.setSessionId(createSessionId())
    await enterRecording(false)
    uni.vibrateShort({ type: 'light' })
  }

  function exitToIdle() {
    stopSilenceWatch()
    flushPendingChunks()
    isEnding = false
    isAutoListenRound = false
    hasSpoken = false
    sentChunkCount = 0
    pendingChunkBuffers = []
    voiceRecorder.stop()
    stopTts()
    voiceStore.reset()
    wsStore.disconnect()
  }

  function onMicClick() {
    if (voiceStore.status === VOICE_STATUS.IDLE) {
      startSession()
    } else {
      exitToIdle()
    }
  }

  function closeVoiceSession() {
    exitToIdle()
  }

  voiceActions = {
    exitToIdle,
    enterAutoListening,
  }

  return {
    voiceStore,
    showVoiceLayer,
    isVoiceActive,
    onMicClick,
    closeVoiceSession,
    VOICE_STATUS,
  }
}
