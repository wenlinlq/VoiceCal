import { ref } from "vue";
import { float32ToInt16 } from "@/utils/audio.js";

const PCM_WORKLET_NAME = "pcm-capture-processor";

const PCM_WORKLET_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel && channel.length) {
      this.port.postMessage(channel)
    }
    return true
  }
}
registerProcessor('${PCM_WORKLET_NAME}', PcmCaptureProcessor)
`;

/**
 * 跨端录音：小程序 PCM 分片；H5 通过 AudioWorklet 采集 PCM
 */
export function useVoiceRecorder() {
  const recording = ref(false);
  let recorder = null;
  let recorderFrameHandler = null;
  let recorderErrorHandler = null;
  let recorderStopHandler = null;
  let stopPromise = null;
  let resolveStop = null;
  let mpStoppedAudioBuffer = null;
  let mpStoppedAudioMeta = null;
  let h5Context = null;
  let h5Stream = null;
  let h5WorkletNode = null;
  let h5Source = null;
  let sampleRate = 16000;

  function resetStoppedAudio() {
    mpStoppedAudioBuffer = null;
    mpStoppedAudioMeta = null;
  }

  function readMpFileAsArrayBuffer(filePath) {
    return new Promise((resolve, reject) => {
      if (!filePath) {
        resolve(null);
        return;
      }
      const fs = uni.getFileSystemManager();
      fs.readFile({
        filePath,
        success: (res) => resolve(res.data || null),
        fail: reject,
      });
    });
  }

  async function start(onFrame) {
    if (recording.value) return sampleRate;

    // #ifdef MP-WEIXIN
    recording.value = true;
    sampleRate = 16000;
    resetStoppedAudio();
    if (!recorder) {
      recorder = uni.getRecorderManager();
    }

    if (recorderFrameHandler && typeof recorder.offFrameRecorded === "function") {
      recorder.offFrameRecorded(recorderFrameHandler);
    }
    if (recorderErrorHandler && typeof recorder.offError === "function") {
      recorder.offError(recorderErrorHandler);
    }
    if (recorderStopHandler && typeof recorder.offStop === "function") {
      recorder.offStop(recorderStopHandler);
    }

    recorderFrameHandler = (res) => {
      if (res.frameBuffer && onFrame) {
        onFrame(res.frameBuffer);
      }
    };
    recorderErrorHandler = (err) => {
      console.error("[recorder] error", err);
      recording.value = false;
      resetStoppedAudio();
      if (resolveStop) {
        resolveStop();
        resolveStop = null;
        stopPromise = null;
      }
    };
    recorderStopHandler = async (res = {}) => {
      recording.value = false;
      mpStoppedAudioMeta = {
        tempFilePath: res.tempFilePath || "",
        duration: Number(res.duration || 0),
        fileSize: Number(res.fileSize || 0),
      };
      try {
        mpStoppedAudioBuffer = await readMpFileAsArrayBuffer(res.tempFilePath);
        console.log("[recorder] stop file ready", {
          duration: mpStoppedAudioMeta.duration,
          fileSize: mpStoppedAudioMeta.fileSize,
          readBytes: mpStoppedAudioBuffer?.byteLength || 0,
        });
      } catch (err) {
        console.warn("[recorder] read stop file failed", err);
        mpStoppedAudioBuffer = null;
      }
      if (resolveStop) {
        resolveStop();
        resolveStop = null;
        stopPromise = null;
      }
    };

    recorder.onFrameRecorded(recorderFrameHandler);
    recorder.onError(recorderErrorHandler);
    recorder.onStop(recorderStopHandler);

    recorder.start({
      duration: 600000,
      sampleRate: 16000,
      numberOfChannels: 1,
      format: "PCM",
      frameSize: 4,
    });
    return sampleRate;
    // #endif

    // #ifdef H5
    recording.value = true;
    sampleRate = await startH5(onFrame);
    return sampleRate;
    // #endif
  }

  // #ifdef H5
  async function loadPcmWorklet(ctx) {
    const url = URL.createObjectURL(
      new Blob([PCM_WORKLET_CODE], { type: "application/javascript" }),
    );
    try {
      await ctx.audioWorklet.addModule(url);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function startH5(onFrame) {
    try {
      h5Stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      h5Context = new (window.AudioContext || window.webkitAudioContext)();

      if (h5Context.state === "suspended") {
        await h5Context.resume();
      }

      if (!h5Context.audioWorklet) {
        throw new Error("当前浏览器不支持 AudioWorklet");
      }

      await loadPcmWorklet(h5Context);

      const rate = h5Context.sampleRate;
      console.log("[recorder] H5 AudioContext sampleRate=", rate);

      h5Source = h5Context.createMediaStreamSource(h5Stream);
      h5WorkletNode = new AudioWorkletNode(h5Context, PCM_WORKLET_NAME);
      h5WorkletNode.port.onmessage = (event) => {
        if (!recording.value) return;
        const float32 = event.data;
        if (!float32 || !float32.length) return;
        const int16 = float32ToInt16(float32);
        if (onFrame) onFrame(int16.buffer, float32);
      };

      h5Source.connect(h5WorkletNode);
      return rate;
    } catch (err) {
      console.error("[recorder] H5 mic error", err);
      recording.value = false;
      stopH5();
      uni.showToast({ title: "无法访问麦克风", icon: "none" });
      throw err;
    }
  }

  function stopH5() {
    if (h5WorkletNode) {
      h5WorkletNode.port.onmessage = null;
      try {
        h5WorkletNode.disconnect();
      } catch (_) {}
      h5WorkletNode = null;
    }
    if (h5Source) {
      try {
        h5Source.disconnect();
      } catch (_) {}
      h5Source = null;
    }
    if (h5Context) {
      h5Context.close().catch(() => {});
      h5Context = null;
    }
    if (h5Stream) {
      h5Stream.getTracks().forEach((t) => t.stop());
      h5Stream = null;
    }
  }
  // #endif

  function stop() {
    if (!recording.value) return Promise.resolve();

    // #ifdef MP-WEIXIN
    if (recorder) {
      if (!stopPromise) {
        stopPromise = new Promise((resolve) => {
          resolveStop = resolve;
          setTimeout(() => {
            if (resolveStop) {
              resolveStop();
              resolveStop = null;
              stopPromise = null;
            }
          }, 1500);
        });
      }
      try {
        recorder.stop();
      } catch (_) {}
      return stopPromise;
    }
    return Promise.resolve();
    // #endif

    // #ifdef H5
    recording.value = false;
    stopH5();
    return Promise.resolve();
    // #endif
  }

  function getSampleRate() {
    return sampleRate;
  }

  function consumeStoppedAudio() {
    const buffer = mpStoppedAudioBuffer;
    mpStoppedAudioBuffer = null;
    return buffer;
  }

  function getStoppedAudioMeta() {
    return mpStoppedAudioMeta;
  }

  return {
    recording,
    start,
    stop,
    getSampleRate,
    consumeStoppedAudio,
    getStoppedAudioMeta,
  };
}
