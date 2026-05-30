import { computed } from "vue";
import { useVoiceStore, VOICE_STATUS } from "@/store/modules/voice.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { useConfirmStore } from "@/store/modules/confirm.js";
import { useVoiceRecorder } from "@/composables/useVoiceRecorder.js";
import { createVoiceWsClient } from "@/composables/useVoiceWsClient.js";
import { DEFAULT_USER_ID } from "@/config/api.js";
import { detectSound, detectSoundFloat } from "@/utils/audio.js";

const RECORD_SILENCE_MS = 3000;
const QUERY_IDLE_EXIT_MS = 10000;
const MAX_RECORDING_MS = 15000;
const EXIT_KEYWORDS = ["退出", "关闭", "结束"];
const NO_VOICE_NUDGE_TEXT = "没有听到，请再说一遍";
const WRITE_DONE_KEYWORDS = [
  "已创建",
  "已删除",
  "已修改",
  "已添加",
  "已取消",
  "已设置",
  "已安排",
  "已为你",
  "已经为你",
  "帮你安排",
  "帮你设置",
  "创建成功",
  "删除成功",
  "修改成功",
];

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

function createSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function getUserId() {
  return DEFAULT_USER_ID;
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

function isWriteCompletionReply(text) {
  if (!text) return false;
  return WRITE_DONE_KEYWORDS.some((kw) => text.includes(kw));
}

function getVoiceActions() {
  return voiceActions;
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

    if (isWriteCompletionReply(voiceStore.replyText)) {
      getVoiceActions()?.scheduleExitAfterAgent();
    } else {
      getVoiceActions()?.scheduleQueryListenAfterAgent();
    }
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
    voiceRecorder.stop();

    try {
      await voiceWs.waitForAgentSpeechDone();
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
    voiceRecorder.stop();
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
    voiceRecorder.stop();

    try {
      await voiceWs.waitForAgentSpeechDone();
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
      voiceWs.sendAudioStart(
        voiceStore.sessionId,
        recordingSampleRate,
        getUserId(),
      );
    }

    if (!audioStreamStarted) return;

    sentChunkCount += 1;
    if (sounded) {
      hasSpoken = true;
      lastSoundAt = Date.now();
    }

    voiceWs.sendAudioChunk(voiceStore.sessionId, frameBuffer, getUserId());
  }

  function startSilenceWatch(isAutoListen) {
    stopSilenceWatch();
    recordingStartedAt = Date.now();
    lastSoundAt = recordingStartedAt;

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
            finishRecordingAndSend();
          }
          return;
        }

        if (voiceStore.needConfirm) {
          if (silentFor >= RECORD_SILENCE_MS) {
            if (hasSpoken && audioStreamStarted) {
              finishRecordingAndSend();
            }
          }
          return;
        }

        if (silentFor >= RECORD_SILENCE_MS) {
          if (hasSpoken && audioStreamStarted) {
            finishRecordingAndSend();
          } else {
            handleNoUserVoice();
          }
        }
        return;
      }

      if (totalFor >= MAX_RECORDING_MS) {
        finishRecordingAndSend();
        return;
      }

      if (hasSpoken && silentFor >= RECORD_SILENCE_MS) {
        finishRecordingAndSend();
      }
    }, 300);
  }

  async function handleNoUserVoice() {
    if (isEnding || userTurnScheduled || isQueryListenRound) return;

    console.log("[voice] no user voice in 3s, nudge agent");
    stopSilenceWatch();
    voiceRecorder.stop();
    isEnding = false;
    hasSpoken = false;
    audioStreamStarted = false;
    sentChunkCount = 0;

    try {
      await voiceWs.ensureConnected(getUserId());
    } catch (err) {
      voiceStore.setError("语音连接已断开");
      return;
    }

    voiceWs.sendText(voiceStore.sessionId, NO_VOICE_NUDGE_TEXT, getUserId());
    voiceStore.setStatus(VOICE_STATUS.THINKING);
  }

  function finishRecordingAndSend() {
    if (isEnding) return;

    if (!hasSpoken || !audioStreamStarted || sentChunkCount === 0) {
      if (isAutoListenRound && !isQueryListenRound) {
        handleNoUserVoice();
      } else if (!isAutoListenRound) {
        voiceStore.setError("未采集到音频，请检查麦克风权限");
      }
      return;
    }

    isEnding = true;
    stopSilenceWatch();
    voiceRecorder.stop();
    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);

    const sent = voiceWs.sendAudioEnd(
      voiceStore.sessionId,
      recordingSampleRate,
      getUserId(),
    );

    if (!sent) {
      isEnding = false;
      voiceStore.setError("语音连接已断开");
      return;
    }

    console.log("[voice] audio_end sent, chunks=", sentChunkCount);
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
      await voiceWs.ensureConnected(getUserId());
      recordingSampleRate = await voiceRecorder.start(onAudioFrame);

      if (!isAuto) {
        audioStreamStarted = true;
        voiceWs.sendAudioStart(
          voiceStore.sessionId,
          recordingSampleRate,
          getUserId(),
        );
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
      await voiceWs.ensureConnected(getUserId());
    } catch (err) {
      console.error("[voice] ws connect fail", err);
      uni.showToast({ title: "无法连接语音服务", icon: "none" });
      return;
    }

    voiceStore.openSession();
    voiceStore.setSessionId(createSessionId());
    await enterRecording(false);
    uni.vibrateShort({ type: "light" });
  }

  function exitToIdle() {
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

  function onMicClick() {
    if (voiceStore.status === VOICE_STATUS.IDLE) {
      startSession();
    } else {
      exitToIdle();
    }
  }

  function closeVoiceSession() {
    exitToIdle();
  }

  async function sendConfirmText(text) {
    confirmStore.hideConfirm();
    stopSilenceWatch();
    voiceRecorder.stop();
    isEnding = false;
    userTurnScheduled = false;
    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);
    voiceStore.needConfirm = false;

    try {
      await voiceWs.ensureConnected(getUserId());
    } catch (err) {
      voiceStore.setError("语音连接已断开");
      return;
    }

    await voiceWs.primeTts(false);
    const sent = voiceWs.sendText(voiceStore.sessionId, text, getUserId());
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
      voiceStore.setSessionId(createSessionId());
    }

    stopSilenceWatch();
    voiceRecorder.stop();
    isEnding = false;
    userTurnScheduled = false;
    isQueryListenRound = false;
    voiceStore.setQueryListenMode(false);

    try {
      await voiceWs.primeTts(true);
      await voiceWs.ensureConnected(getUserId());
    } catch (err) {
      uni.showToast({ title: "无法连接语音服务", icon: "none" });
      return;
    }

    voiceWs.sendText(voiceStore.sessionId, text.trim(), getUserId());
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
