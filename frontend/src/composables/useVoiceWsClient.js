import { useWebSocketStore } from "@/store/modules/websocket.js";
import { VoiceTtsPlayer } from "@/utils/voice-tts-player.js";
import { arrayBufferToBase64 } from "@/utils/audio.js";

/**
 * WebSocket 语音客户端（协议对齐 voice_ws_test.html）
 *
 * 发送: audio_start / audio.chunk / audio.end / text.message
 * 接收: transcription / agent.reply / tts.chunk / turn.done / error
 */
export function createVoiceWsClient(handlers = {}) {
  const wsStore = useWebSocketStore();
  const ttsPlayer = new VoiceTtsPlayer();
  let connectPromise = null;
  let ttsReceivedThisTurn = false;

  function sendJson(payload) {
    return wsStore.send(payload);
  }

  async function ensureConnected(userId) {
    if (wsStore.connected && wsStore.socketTask) {
      return;
    }
    if (wsStore.connecting && connectPromise) {
      return connectPromise;
    }
    connectPromise = wsStore.connect(userId).finally(() => {
      connectPromise = null;
    });
    return connectPromise;
  }

  function disconnect() {
    connectPromise = null;
    wsStore.disconnect();
  }

  async function primeTts(fromUserGesture = true) {
    await ttsPlayer.prime(fromUserGesture);
  }

  function resetTtsTurn() {
    ttsReceivedThisTurn = false;
    ttsPlayer.reset();
  }

  function stopTts() {
    ttsPlayer.stopPlayback();
    ttsPlayer.reset();
    ttsReceivedThisTurn = false;
  }

  /** Agent 本轮 TTS 播完（或无 TTS）后再开用户麦 */
  async function waitForAgentSpeechDone() {
    // turn.done 后音频分片可能仍在路上，短暂等待
    await new Promise((r) => setTimeout(r, 150));
    for (let i = 0; i < 30; i++) {
      if (ttsReceivedThisTurn) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    ttsPlayer.markTurnDone();
    if (!ttsPlayer.hasAudio) return;
    await ttsPlayer.waitUntilIdle(60000);
  }

  function sendAudioStart(sessionId, sampleRate, userId) {
    return sendJson({
      type: "audio_start",
      session_id: sessionId,
      user_id: userId,
      format: "pcm_s16le",
      sampleRate,
    });
  }

  function sendAudioChunk(sessionId, frameBuffer, userId) {
    return sendJson({
      type: "audio.chunk",
      session_id: sessionId,
      user_id: userId,
      data: arrayBufferToBase64(frameBuffer),
    });
  }

  function sendAudioEnd(sessionId, sampleRate, userId) {
    return sendJson({
      type: "audio.end",
      session_id: sessionId,
      user_id: userId,
      sample_rate: sampleRate,
    });
  }

  function sendText(sessionId, text, userId) {
    resetTtsTurn();
    return sendJson({
      type: "text.message",
      session_id: sessionId,
      user_id: userId,
      text,
    });
  }

  async function handleMessage(msg) {
    const type = msg.type;

    if (type === "transcription") {
      handlers.onTranscription?.(msg.text || "");
      return;
    }

    if (type === "agent.reply") {
      handlers.onAgentReply?.(msg.text || "", Boolean(msg.need_confirm));
      return;
    }

    if (type === "tts.chunk") {
      const played = await ttsPlayer.pushChunk(msg.data, Boolean(msg.is_last));
      if (played) {
        ttsReceivedThisTurn = true;
        handlers.onTtsStart?.();
      }
      return;
    }

    if (type === "turn.done") {
      handlers.onTurnDone?.(Boolean(msg.success));
      return;
    }

    if (type === "error") {
      handlers.onError?.(msg.message || "语音处理失败");
      return;
    }
  }

  function bindMessageHandler() {
    wsStore.setMessageHandler((msg) => {
      handleMessage(msg).catch((err) => {
        console.error("[voice-ws] handleMessage error", err, msg);
      });
    });
  }

  bindMessageHandler();

  return {
    ensureConnected,
    disconnect,
    primeTts,
    resetTtsTurn,
    stopTts,
    waitForAgentSpeechDone,
    sendAudioStart,
    sendAudioChunk,
    sendAudioEnd,
    sendText,
  };
}
