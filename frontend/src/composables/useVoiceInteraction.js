import { computed, ref } from 'vue'
import { useVoiceStore, VOICE_STATUS } from '@/store/modules/voice.js'

/** 静态演示常量 */
const RECORD_SILENCE_MS = 3000
const AUTO_LISTEN_SILENCE_MS = 10000
const MOCK_THINKING_MS = 1200
const MOCK_SPEAKING_MS = 2200

const MOCK_USER_TEXT = '明天下午三点开项目会议'
const MOCK_REPLY_TEXT = '好的，已为你添加明天下午三点的项目会议。还有其他安排吗？'
const EXIT_KEYWORDS = ['退出', '关闭']

/** 模块级单例 */
const agentState = ref('listening')
let mockTimers = []
let silenceTimer = null

function clearAllTimers() {
  mockTimers.forEach(clearTimeout)
  mockTimers = []
  if (silenceTimer) {
    clearTimeout(silenceTimer)
    silenceTimer = null
  }
}

function scheduleTimer(fn, ms) {
  const id = setTimeout(fn, ms)
  mockTimers.push(id)
  return id
}

export function useVoiceInteraction() {
  const voiceStore = useVoiceStore()

  const showVoiceLayer = computed(() => voiceStore.sessionOpen)

  const isVoiceActive = computed(() => voiceStore.status !== VOICE_STATUS.IDLE)

  function scheduleSilenceTimeout(isAutoListen) {
    if (silenceTimer) clearTimeout(silenceTimer)
    const ms = isAutoListen ? AUTO_LISTEN_SILENCE_MS : RECORD_SILENCE_MS
    silenceTimer = setTimeout(() => {
      silenceTimer = null
      onSilenceTimeout(isAutoListen)
    }, ms)
  }

  /** 录音中：3 秒无声音 → 思考中；自动聆听：10 秒无声音 → 空闲 */
  function onSilenceTimeout(isAutoListen) {
    if (isAutoListen) {
      exitToIdle()
      return
    }
    if (voiceStore.status === VOICE_STATUS.RECORDING) {
      enterThinking()
    }
  }

  /** 静态模拟：识别到退出关键词 */
  function mockCheckExitKeyword(text) {
    return EXIT_KEYWORDS.some((kw) => text.includes(kw))
  }

  function enterRecording(isAuto = false) {
    voiceStore.setStatus(isAuto ? VOICE_STATUS.AUTO_LISTENING : VOICE_STATUS.RECORDING)
    agentState.value = 'listening'
    if (!isAuto) {
      voiceStore.clearTurn()
    }
    scheduleSilenceTimeout(isAuto)

    // 静态演示：自动聆听阶段 4 秒后模拟用户说「退出」
    if (isAuto) {
      scheduleTimer(() => {
        if (voiceStore.status !== VOICE_STATUS.AUTO_LISTENING) return
        voiceStore.setUserText('退出')
        if (mockCheckExitKeyword('退出')) {
          exitToIdle()
        }
      }, 4000)
    }
  }

  function enterThinking() {
    if (silenceTimer) {
      clearTimeout(silenceTimer)
      silenceTimer = null
    }
    voiceStore.setStatus(VOICE_STATUS.THINKING)
    agentState.value = 'thinking'

    scheduleTimer(() => {
      voiceStore.setUserText(MOCK_USER_TEXT)
    }, MOCK_THINKING_MS * 0.4)

    scheduleTimer(() => {
      voiceStore.setReplyText(MOCK_REPLY_TEXT)
      enterSpeaking()
    }, MOCK_THINKING_MS)
  }

  function enterSpeaking() {
    voiceStore.setStatus(VOICE_STATUS.SPEAKING)
    agentState.value = 'speaking'

    scheduleTimer(() => {
      enterAutoListening()
    }, MOCK_SPEAKING_MS)
  }

  function enterAutoListening() {
    enterRecording(true)
  }

  function startSession() {
    clearAllTimers()
    voiceStore.openSession()
    enterRecording(false)
    uni.vibrateShort({ type: 'light' })
  }

  function exitToIdle() {
    clearAllTimers()
    voiceStore.reset()
    agentState.value = 'listening'
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

  return {
    voiceStore,
    showVoiceLayer,
    isVoiceActive,
    onMicClick,
    closeVoiceSession,
    VOICE_STATUS,
  }
}
