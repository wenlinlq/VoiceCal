import { base64ToArrayBuffer, pcmToWav } from '@/utils/audio.js'

const TTS_SAMPLE_RATE = 24000
const TTS_START_BUFFER_SECONDS = 0.45
const TTS_RESUME_BUFFER_SECONDS = 0.25

/** 流式 TTS 播放器（逻辑来自 voice_ws_test.html） */
export class VoiceTtsPlayer {
  constructor() {
    this.ttsSampleRate = TTS_SAMPLE_RATE
    this.chunks = []
    this.pendingQueue = []
    this.queuedSeconds = 0
    this.playbackStarted = false
    this.hasAudio = false
    this.turnDone = false
    this.streamEnded = false
    this.playbackContext = null
    this.playbackCursor = 0
    this.activeSources = new Set()
    this.idleWaiters = []
    // #ifdef MP-WEIXIN
    this.innerAudio = null
    this.mpPlaying = false
    // #endif
  }

  reset() {
    this.stopPlayback()
    this.chunks = []
    this.pendingQueue = []
    this.queuedSeconds = 0
    this.playbackStarted = false
    this.hasAudio = false
    this.turnDone = false
    this.streamEnded = false
    this.idleWaiters = []
  }

  /** turn.done 后调用，允许在收齐/播完音频后进入用户轮次 */
  markTurnDone() {
    this.turnDone = true
    this.streamEnded = true
    this.checkNotifyIdle()
  }

  isPlaybackIdle() {
    if (!this.turnDone) return false
    if (!this.hasAudio) return true
    if (!this.streamEnded) return false
    // #ifdef H5
    return this.activeSources.size === 0 && this.pendingQueue.length === 0
    // #endif
    // #ifdef MP-WEIXIN
    return !this.mpPlaying
    // #endif
  }

  waitUntilIdle(timeoutMs = 60000) {
    if (this.isPlaybackIdle()) {
      return Promise.resolve()
    }

    return new Promise((resolve) => {
      this.idleWaiters.push(resolve)
      if (timeoutMs > 0) {
        setTimeout(() => this.notifyIdle(), timeoutMs)
      }
    })
  }

  notifyIdle() {
    if (!this.isPlaybackIdle()) return
    const waiters = this.idleWaiters.splice(0)
    waiters.forEach((fn) => fn())
  }

  checkNotifyIdle() {
    if (this.isPlaybackIdle()) {
      this.notifyIdle()
    }
  }

  async prime(fromUserGesture = false) {
    // #ifdef H5
    if (!this.playbackContext) {
      this.playbackContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.ttsSampleRate,
      })
    }
    if (fromUserGesture && this.playbackContext.state === 'suspended') {
      await this.playbackContext.resume()
    }
    // #endif
  }

  stopPlayback() {
    // #ifdef H5
    for (const source of this.activeSources) {
      try {
        source.onended = null
        source.stop()
      } catch (_) {}
    }
    this.activeSources.clear()
    this.playbackCursor = 0
    // #endif
    // #ifdef MP-WEIXIN
    this.mpPlaying = false
    if (this.innerAudio) {
      try {
        this.innerAudio.stop()
      } catch (_) {}
    }
    // #endif
  }

  pcmBytesToAudioBuffer(audioCtx, bytes) {
    const frameCount = Math.floor(bytes.byteLength / 2)
    if (frameCount <= 0) return null
    const buffer = audioCtx.createBuffer(1, frameCount, this.ttsSampleRate)
    const channelData = buffer.getChannelData(0)
    const pcmView = new DataView(bytes.buffer, bytes.byteOffset, frameCount * 2)
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = pcmView.getInt16(i * 2, true) / 32768.0
    }
    return buffer
  }

  /**
   * 收到 tts.chunk
   * 空 data / 空 bytes 的占位包（含 is_last:true）直接忽略，对齐 voice_ws_test.html
   */
  async pushChunk(base64Data, isLast = false) {
    if (!base64Data) {
      return false
    }

    const bytes = new Uint8Array(base64ToArrayBuffer(base64Data))
    if (!bytes.length) {
      return false
    }

    this.hasAudio = true
    if (isLast) {
      this.streamEnded = true
    }

    this.chunks.push(bytes)
    const durationSeconds = bytes.byteLength / 2 / this.ttsSampleRate
    this.pendingQueue.push({
      bytes,
      isLast: Boolean(isLast),
      index: this.chunks.length,
      durationSeconds,
    })
    this.queuedSeconds += durationSeconds

    // #ifdef H5
    await this.flushQueue(true)
    // #endif

    // #ifdef MP-WEIXIN
    if (isLast) {
      await this.playAllMp()
    }
    // #endif

    return true
  }

  // #ifdef H5
  async flushQueue(auto = true) {
    const audioCtx = await this.ensureContext(false)
    if (!audioCtx || audioCtx.state === 'suspended') {
      return false
    }

    const needsRestart = this.playbackCursor <= audioCtx.currentTime + 0.02
    const minBufferSeconds = this.playbackStarted
      ? TTS_RESUME_BUFFER_SECONDS
      : TTS_START_BUFFER_SECONDS

    if (!this.streamEnded && this.queuedSeconds < minBufferSeconds && needsRestart) {
      return false
    }

    if (needsRestart) {
      this.playbackCursor = audioCtx.currentTime + 0.05
    }

    while (this.pendingQueue.length > 0) {
      const item = this.pendingQueue.shift()
      const buffer = this.pcmBytesToAudioBuffer(audioCtx, item.bytes)
      if (!buffer) continue

      this.playbackStarted = true
      this.queuedSeconds = Math.max(0, this.queuedSeconds - buffer.duration)

      const source = audioCtx.createBufferSource()
      source.buffer = buffer
      source.connect(audioCtx.destination)

      const startAt = Math.max(this.playbackCursor, audioCtx.currentTime + 0.03)
      this.playbackCursor = startAt + buffer.duration
      this.activeSources.add(source)
      source.onended = () => {
        this.activeSources.delete(source)
        this.checkNotifyIdle()
      }
      source.start(startAt)
    }

    this.checkNotifyIdle()
    return true
  }

  async ensureContext(fromUserGesture) {
    await this.prime(fromUserGesture)
    return this.playbackContext
  }
  // #endif

  // #ifdef MP-WEIXIN
  async playAllMp() {
    if (!this.chunks.length) {
      this.streamEnded = true
      this.checkNotifyIdle()
      return
    }
    const totalLen = this.chunks.reduce((s, c) => s + c.length, 0)
    const merged = new Uint8Array(totalLen)
    let offset = 0
    for (const chunk of this.chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }
    const wav = pcmToWav(merged.buffer, this.ttsSampleRate)
    if (!this.innerAudio) {
      this.innerAudio = uni.createInnerAudioContext()
      this.innerAudio.onError((err) => {
        console.warn('[tts] play error', err)
        this.mpPlaying = false
        this.checkNotifyIdle()
      })
      this.innerAudio.onEnded(() => {
        this.mpPlaying = false
        this.checkNotifyIdle()
      })
    }
    const fs = uni.getFileSystemManager()
    const filePath = `${uni.env.USER_DATA_PATH}/tts_${Date.now()}.wav`
    fs.writeFile({
      filePath,
      data: wav,
      success: () => {
        this.mpPlaying = true
        this.innerAudio.src = filePath
        this.innerAudio.play()
      },
      fail: (err) => {
        console.warn('[tts] write file fail', err)
        this.checkNotifyIdle()
      },
    })
  }
  // #endif
}
