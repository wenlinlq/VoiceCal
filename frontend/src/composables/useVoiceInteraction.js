import { computed } from "vue";
import { useVoiceStore, VOICE_STATUS } from "@/store/modules/voice.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { useConfirmStore } from "@/store/modules/confirm.js";
import { useVoiceRecorder } from "@/composables/useVoiceRecorder.js";
import { createVoiceWsClient } from "@/composables/useVoiceWsClient.js";
import { useUserStore } from "@/store/modules/user.js";
import { getCachedLoginInfo, isMpWeixin } from "@/utils/wechat-login.js";
import {
  detectSound,
  detectSoundFloat,
  mergeArrayBuffers,
} from "@/utils/audio.js";

const RECORD_SILENCE_MS = 3000;
const QUERY_IDLE_EXIT_MS = 10000;
const MAX_RECORDING_MS = 15000;
const CHUNK_SEND_INTERVAL_MS = 200;
const UPLOAD_CHUNK_BYTES = 32000;
const AUTO_LISTEN_RESUME_DELAY_MS = 450;
const EXIT_KEYWORDS = ["退出", "关闭", "结束"];
const NO_VOICE_NUDGE_TEXT = "没有听到，请再说一遍";

const voiceRecorder = useVoiceRecorder();
let silenceWatchTimer = null;
let isAutoListenRound = false;
let isQueryListenRound = false;
let isEnding = false;
let hasSpoken = false;
let audioStreamStarted = false;
let sentChunkCount = 0;
let recordingSampleRate = 16000;
let recordingStartedAt = 0;
let lastSoundAt = 0;
let userTurnScheduled = false;
let voiceActions = null;
let pendingChunkBuffers = [];
let lastChunkSendAt = 0;
let activeConversationSessionId = "";

function createSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function getConversationSessionId(forceNew = false) {
  if (forceNew || !activeConversationSessionId) {
    activeConversationSessionId = createSessionId();
  }
  return activeConversationSessionId;
}

async function getAuthToken() {
  const userStore = useUserStore();
  if (userStore.token) {
    return userStore.token;
  }

  const cached = getCachedLoginInfo();
  if (cached?.token) {
    userStore.applyLoginInfo(cached);
    return cached.token;
  }

  try {
    const loginInfo = await userStore.ensureAuth();
    return loginInfo?.token || "";
  } catch (err) {
    console.warn("[voice] ensureAuth failed", err);
    return "";
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function stopSilenceWatch() {
  if (silenceWatchTimer) {
    clearInterval(silenceWatchTimer);
    silenceWatchTimer = null;
  }
}

function checkExitKeyword(text) {
  if (!text) return false;
  return EXIT_KEYWORDS.some((kw) => text.includes(kw));
}

function getVoiceActions() {
  return voiceActions;
}

function resetPendingChunks() {
  pendingChunkBuffers = [];
  lastChunkSendAt = 0;
}

function normalizePcmBuffer(audioBuffer) {
  if (!audioBuffer || audioBuffer.byteLength < 2) {
    return new ArrayBuffer(0);
  }

  const view = new DataView(audioBuffer);
  if (
    audioBuffer.byteLength >= 44 &&
    view.getUint32(0, false) === 0x52494646 &&
    view.getUint32(8, false) === 0x57415645
  ) {
    let offset = 12;
    while (offset + 8 <= audioBuffer.byteLength) {
      const chunkId = view.getUint32(offset, false);
      const chunkSize = view.getUint32(offset + 4, true);
      offset += 8;
      if (chunkId === 0x64617461) {
        return audioBuffer.slice(offset, offset + chunkSize);
      }
      offset += chunkSize;
      if (chunkSize % 2 === 1) offset += 1;
    }
  }

  return audioBuffer;
}

function sendBufferedAudio(sessionId, sampleRate, audioBuffer) {
  const normalizedBuffer = normalizePcmBuffer(audioBuffer);
  if (!normalizedBuffer || normalizedBuffer.byteLength < 2) {
    return { ok: false, chunkCount: 0, totalBytes: 0 };
  }

  const started = voiceWs.sendAudioStart(sessionId, sampleRate);
  if (!started) {
    return { ok: false, chunkCount: 0, totalBytes: normalizedBuffer.byteLength };
  }

  let chunkCount = 0;
  for (let offset = 0; offset < normalizedBuffer.byteLength; offset += UPLOAD_CHUNK_BYTES) {
    const end = Math.min(offset + UPLOAD_CHUNK_BYTES, normalizedBuffer.byteLength);
    const chunk = normalizedBuffer.slice(offset, end);
    const sent = voiceWs.sendAudioChunk(sessionId, chunk);
    if (!sent) {
      return { ok: false, chunkCount, totalBytes: normalizedBuffer.byteLength };
    }
    chunkCount += 1;
  }

  const ended = voiceWs.sendAudioEnd(sessionId, sampleRate);
  return { ok: Boolean(ended), chunkCount, totalBytes: normalizedBuffer.byteLength };
}

const voiceWs = createVoiceWsClient({
  onTranscription(text) {
    const voiceStore = useVoiceStore();
    voiceStore.setUserText(text);
    if (checkExitKeyword(text)) {
      getVoiceActions()?.exitToIdle();
    }
  },

  onAgentReply(text, needConfirm) {
    const voiceStore = useVoiceStore();
    voiceStore.setReplyText(text, needConfirm);
    if (needConfirm) {
      useConfirmStore().showConfirm(null, text);
    }
  },

  onTtsStart() {
    const voiceStore = useVoiceStore();
    if (voiceStore.status !== VOICE_STATUS.IDLE) {
      voiceStore.setStatus(VOICE_STATUS.SPEAKING);
    }
  },

  onTurnDone(success) {
    isEnding = false;
    const voiceStore = useVoiceStore();

    if (!success) {
      getVoiceActions()?.scheduleUserTurnAfterAgent(false);
      return;
    }

    if (voiceStore.needConfirm) {
      getVoiceActions()?.scheduleUserTurnAfterAgent(false);
      return;
    }

    useCalendarStore()
      .syncAfterVoiceTurn()
      .catch((err) => console.warn("[voice] sync calendar failed", err));

    getVoiceActions()?.scheduleQueryListenAfterAgent();
  },

  onError(message) {
    isEnding = false;
    const voiceStore = useVoiceStore();
    if (
      message.includes("empty transcription") ||
      message.includes("empty text")
    ) {
      voiceStore.setError("没有听清，请再来说一次");
    } else {
      voiceStore.setError(message);
    }
    setTimeout(() => {
      if (!voiceStore.sessionOpen) return;
      getVoiceActions()?.scheduleUserTurnAfterAgent(false);
    }, 800);
  },
});

export function useVoiceInteraction() {
  const voiceStore = useVoiceStore();
  const confirmStore = useConfirmStore();

  const showVoiceLayer = computed(() => voiceStore.sessionOpen);
  const isVoiceActive = computed(() => voiceStore.status !== VOICE_STATUS.IDLE);

  /** 待确认 / 出错：播完后继续开麦 */
  async function scheduleUserTurnAfterAgent(queryMode = false) {
    if (!voiceStore.sessionOpen || userTurnScheduled) return;

    userTurnScheduled = true;
    stopSilenceWatch();
    await voiceRecorder.stop();
    resetPendingChunks();

    try {
      await voiceWs.waitForAgentSpeechDone();
      if (!voiceStore.sessionOpen) return;
      await delay(AUTO_LISTEN_RESUME_DELAY_MS);
      if (!voiceStore.sessionOpen) return;
      await enterAutoListening(queryMode);
    } catch (err) {
      console.error("[voice] scheduleUserTurnAfterAgent failed", err);
    } finally {
      userTurnScheduled = false;
    }
  }

  /** 增删改完成：播完后自动断开 WS */
  async function scheduleExitAfterAgent() {
    if (!voiceStore.sessionOpen || userTurnScheduled) return;

    userTurnScheduled = true;
    stopSilenceWatch();
    await voiceRecorder.stop();
    resetPendingChunks();
    voiceStore.setQueryListenMode(false);
    isQueryListenRound = false;

    try {
      await voiceWs.waitForAgentSpeechDone();
      if (!voiceStore.sessionOpen) return;
      console.log("[voice] write op done, auto exit");
      exitToIdle();
    } catch (err) {
      console.error("[voice] scheduleExitAfterAgent failed", err);
      exitToIdle();
    } finally {
      userTurnScheduled = false;
    }
  }

  /** 查询完成：播完后开麦，等用户说结束或 10s 无声音再退出 */
  async function scheduleQueryListenAfterAgent() {
    if (!voiceStore.sessionOpen || userTurnScheduled) return;

    userTurnScheduled = true;
    stopSilenceWatch();
    await voiceRecorder.stop();
    resetPendingChunks();

    try {
      await voiceWs.waitForAgentSpeechDone();
      if (!voiceStore.sessionOpen) return;
      await delay(AUTO_LISTEN_RESUME_DELAY_MS);
      if (!voiceStore.sessionOpen) return;
      await enterAutoListening(true);
    } catch (err) {
      console.error("[voice] scheduleQueryListenAfterAgent failed", err);
    } finally {
      userTurnScheduled = false;
    }
  }

  function onAudioFrame(frameBuffer, float32) {
    if (!voiceStore.sessionOpen || isEnding) return;

    const sounded = float32
      ? detectSoundFloat(float32)
      : detectSound(frameBuffer);

    if (isAutoListenRound && !audioStreamStarted) {
      if (!sounded) return;
      audioStreamStarted = true;
      hasSpoken = true;
      lastSoundAt = Date.now();
      sentChunkCount = 0;
      if (!isMpWeixin()) {
        voiceWs.sendAudioStart(voiceStore.sessionId, recordingSampleRate);
      }
    }

    if (!audioStreamStarted) return;

    if (sounded) {
      hasSpoken = true;
      lastSoundAt = Date.now();
    }

    if (isMpWeixin()) return;

    pendingChunkBuffers.push(frameBuffer);
    const now = Date.now();
    if (now - lastChunkSendAt >= CHUNK_SEND_INTERVAL_MS) {
      flushPendingChunks();
    }
  }

  function flushPendingChunks() {
    if (!pendingChunkBuffers.length) return false;
    const merged = mergeArrayBuffers(pendingChunkBuffers);
    pendingChunkBuffers = [];
    const sent = voiceWs.sendAudioChunk(voiceStore.sessionId, merged);
    if (sent) {
      sentChunkCount += 1;
      lastChunkSendAt = Date.now();
      return true;
    }
    return false;
  }

  function startSilenceWatch(isAutoListen) {
    stopSilenceWatch();
    recordingStartedAt = Date.now();
    lastSoundAt = recordingStartedAt;
    resetPendingChunks();

    silenceWatchTimer = setInterval(() => {
      if (!voiceStore.sessionOpen || isEnding) return;

      const status = voiceStore.status;
      if (
        status !== VOICE_STATUS.RECORDING &&
        status !== VOICE_STATUS.AUTO_LISTENING
      ) {
        return;
      }

      const now = Date.now();
      const silentFor = now - lastSoundAt;
      const totalFor = now - recordingStartedAt;

      if (isAutoListen) {
        if (isQueryListenRound) {
          if (!hasSpoken && silentFor >= QUERY_IDLE_EXIT_MS) {
            console.log("[voice] query idle 10s, auto exit");
            exitToIdle();
            return;
          }
          if (
            hasSpoken &&
            audioStreamStarted &&
            silentFor >= RECORD_SILENCE_MS
          ) {
            isQueryListenRound = false;
            voiceStore.setQueryListenMode(false);
            void finishRecordingAndSend();
          }
          return;
        }

        if (voiceStore.needConfirm) {
          if (silentFor >= RECORD_SILENCE_MS) {
            if (hasSpoken && audioStreamStarted) {
              void finishRecordingAndSend();
            }
          }
          return;
        }

        if (silentFor >= RECORD_SILENCE_MS) {
          if (hasSpoken && audioStreamStarted) {
            void finishRecordingAndSend();
          } else {
            handleNoUserVoice();
          }
        }
        return;
      }

      if (totalFor >= MAX_RECORDING_MS) {
        void finishRecordingAndSend();
        return;
      }

      if (hasSpoken && silentFor >= RECORD_SILENCE_MS) {
        void finishRecordingAndSend();
      }
    }, 300);
  }

  async function handleNoUserVoice() {
    if (isEnding || userTurnScheduled || isQueryListenRound) return;

    console.log("[voice] no user voice in 3s, nudge agent");
    stopSilenceWatch();
    await voiceRecorder.stop();
    isEnding = false;
    hasSpoken = false;
    audioStreamStarted = false;
    sentChunkCount = 0;
    resetPendingChunks();

    try {
      await voiceWs.ensureConnected(await getAuthToken());
    } catch (err) {
      voiceStore.setError("语音连接已断开");
      return;
    }

    voiceStore.beginAgentTurn();
    voiceWs.sendText(voiceStore.sessionId, NO_VOICE_NUDGE_TEXT);
    voiceStore.setStatus(VOICE_STATUS.THINKING);
  }

  async function finishRecordingAndSend() {
    if (isEnding) return;

    console.log("[voice] finishRecordingAndSend start", {
      status: voiceStore.status,
      sessionId: voiceStore.sessionId,
    });
    isEnding = true;
    stopSilenceWatch();
    await voiceRecorder.stop();
    flushPendingChunks();
    const stoppedAudioBuffer = voiceRecorder.consumeStoppedAudio();
    const stoppedAudioMeta = voiceRecorder.getStoppedAudioMeta();

    if (isMpWeixin()) {
      console.log("[voice] mp stop audio", {
        duration: stoppedAudioMeta?.duration || 0,
        fileSize: stoppedAudioMeta?.fileSize || 0,
        readBytes: stoppedAudioBuffer?.byteLength || 0,
      });
    }

    const hasMpStoppedAudio = Boolean(
      isMpWeixin() &&
        stoppedAudioBuffer &&
        stoppedAudioBuffer.byteLength >= 2,
    );

    if (
      !hasMpStoppedAudio &&
      (!hasSpoken || !audioStreamStarted || sentChunkCount === 0)
    ) {
      console.warn("[voice] finishRecordingAndSend aborted", {
        hasSpoken,
        audioStreamStarted,
        sentChunkCount,
      });
      isEnding = false;
      if (isAutoListenRound && !isQueryListenRound) {
        handleNoUserVoice();
      } else if (!isAutoListenRound) {
        voiceStore.setError("未采集到音频，请检查麦克风权限");
      }
      return;
    }

    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);
    flushPendingChunks();

    let sent = false;
    if (hasMpStoppedAudio) {
      const upload = sendBufferedAudio(
        voiceStore.sessionId,
        recordingSampleRate,
        stoppedAudioBuffer,
      );
      sentChunkCount = upload.chunkCount;
      sent = upload.ok;
      console.log("[voice] mp buffered upload", upload);
    } else {
      sent = voiceWs.sendAudioEnd(
        voiceStore.sessionId,
        recordingSampleRate,
      );
    }

    if (!sent) {
      isEnding = false;
      voiceStore.setError("语音连接已断开");
      return;
    }

    console.log("[voice] audio_end sent, chunks=", sentChunkCount);
    if (voiceStore.needConfirm) {
      confirmStore.hideConfirm();
      voiceStore.needConfirm = false;
    }
    voiceStore.beginAgentTurn();
    voiceStore.setStatus(VOICE_STATUS.THINKING);
  }

  async function enterRecording(isAuto = false, queryMode = false) {
    if (!voiceStore.sessionOpen) return;

    isAutoListenRound = isAuto;
    isQueryListenRound = isAuto && queryMode;
    isEnding = false;
    hasSpoken = false;
    audioStreamStarted = false;
    sentChunkCount = 0;
    resetPendingChunks();
    voiceStore.setQueryListenMode(isQueryListenRound);

    voiceStore.setStatus(
      isAuto ? VOICE_STATUS.AUTO_LISTENING : VOICE_STATUS.RECORDING,
    );

    if (!isAuto) {
      voiceStore.clearTurn();
    } else {
      voiceStore.errorText = "";
    }

    try {
      await voiceWs.ensureConnected(await getAuthToken());
      recordingSampleRate = await voiceRecorder.start(onAudioFrame);

      if (!isAuto) {
        audioStreamStarted = true;
        if (!isMpWeixin()) {
          voiceWs.sendAudioStart(voiceStore.sessionId, recordingSampleRate);
        }
      }

      startSilenceWatch(isAuto);
    } catch (err) {
      console.error("[voice] enterRecording failed", err);
      voiceStore.setError("无法启动录音");
      exitToIdle();
    }
  }

  async function enterAutoListening(queryMode = false) {
    if (!voiceStore.sessionOpen) return;
    await enterRecording(true, queryMode);
  }

  async function startSession() {
    try {
      voiceWs.resetTtsTurn();
      await voiceWs.primeTts(true);
      await voiceWs.ensureConnected(await getAuthToken());
    } catch (err) {
      console.error("[voice] ws connect fail", err);
      uni.showToast({ title: "无法连接语音服务", icon: "none" });
      return;
    }

    voiceStore.openSession();
    voiceStore.setSessionId(getConversationSessionId());
    await enterRecording(false);
    uni.vibrateShort({ type: "light" });
  }

  function exitToIdle() {
    console.log("[voice] exitToIdle", {
      status: voiceStore.status,
      sessionId: voiceStore.sessionId,
    });
    stopSilenceWatch();
    isEnding = false;
    userTurnScheduled = false;
    isAutoListenRound = false;
    isQueryListenRound = false;
    hasSpoken = false;
    audioStreamStarted = false;
    sentChunkCount = 0;
    voiceRecorder.stop();
    voiceWs.stopTts();
    confirmStore.hideConfirm();
    voiceStore.reset();
    voiceWs.disconnect();
  }

  async function onMicClick() {
    console.log("[voice] onMicClick", {
      status: voiceStore.status,
      sessionOpen: voiceStore.sessionOpen,
      isEnding,
    });
    if (voiceStore.status === VOICE_STATUS.IDLE) {
      await startSession();
      return;
    }

    if (
      voiceStore.status === VOICE_STATUS.RECORDING ||
      voiceStore.status === VOICE_STATUS.AUTO_LISTENING
    ) {
      if (isEnding) return;
      await finishRecordingAndSend();
      return;
    }

    exitToIdle();
  }

  function closeVoiceSession() {
    exitToIdle();
  }

  async function sendConfirmText(text) {
    confirmStore.hideConfirm();
    stopSilenceWatch();
    await voiceRecorder.stop();
    isEnding = false;
    userTurnScheduled = false;
    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);
    voiceStore.needConfirm = false;

    try {
      await voiceWs.ensureConnected(await getAuthToken());
    } catch (err) {
      voiceStore.setError("语音连接已断开");
      return;
    }

    await voiceWs.primeTts(false);
    voiceStore.beginAgentTurn();
    const sent = voiceWs.sendText(voiceStore.sessionId, text);
    if (!sent) {
      voiceStore.setError("语音连接已断开");
      return;
    }
    voiceStore.setStatus(VOICE_STATUS.THINKING);
  }

  async function sendVoiceText(text) {
    if (!text?.trim()) return;

    if (!voiceStore.sessionOpen) {
      voiceStore.openSession();
      voiceStore.setSessionId(getConversationSessionId());
    }

    stopSilenceWatch();
    await voiceRecorder.stop();
    isEnding = false;
    userTurnScheduled = false;
    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);

    try {
      await voiceWs.primeTts(true);
      await voiceWs.ensureConnected(await getAuthToken());
    } catch (err) {
      uni.showToast({ title: "无法连接语音服务", icon: "none" });
      return;
    }

    voiceStore.beginAgentTurn();
    voiceWs.sendText(voiceStore.sessionId, text.trim());
    voiceStore.setStatus(VOICE_STATUS.THINKING);
  }

  function onVoiceConfirm() {
    sendConfirmText("确认");
  }

  function onVoiceCancel() {
    sendConfirmText("取消");
  }

  voiceActions = {
    exitToIdle,
    enterAutoListening,
    scheduleUserTurnAfterAgent,
    scheduleExitAfterAgent,
    scheduleQueryListenAfterAgent,
    sendConfirmText,
  };

  return {
    voiceStore,
    showVoiceLayer,
    isVoiceActive,
    onMicClick,
    closeVoiceSession,
    onVoiceConfirm,
    onVoiceCancel,
    sendVoiceText,
    VOICE_STATUS,
  };
}
