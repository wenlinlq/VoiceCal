/** ArrayBuffer → base64（跨端） */
export function arrayBufferToBase64(buffer) {
  if (!buffer) return "";
  // #ifdef MP-WEIXIN
  return uni.arrayBufferToBase64(buffer);
  // #endif
  // #ifndef MP-WEIXIN
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
  // #endif
}

/** base64 → ArrayBuffer */
export function base64ToArrayBuffer(base64) {
  if (!base64) return new ArrayBuffer(0);
  // #ifdef MP-WEIXIN
  return uni.base64ToArrayBuffer(base64);
  // #endif
  // #ifndef MP-WEIXIN
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
  // #endif
}

/** Float32 单声道 → Int16 PCM */
export function float32ToInt16(float32) {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16;
}

/** 检测 Float32 帧是否含有效声音（峰值检测，抗环境底噪） */
export function detectSoundFloat(float32, peakThreshold = 0.025) {
  if (!float32 || !float32.length) return false;
  let peak = 0;
  for (let i = 0; i < float32.length; i++) {
    const amp = Math.abs(float32[i]);
    if (amp > peak) peak = amp;
  }
  return peak > peakThreshold;
}

/** 检测 PCM 帧是否含有效声音（简易 VAD，峰值检测） */
export function detectSound(frameBuffer, peakThreshold = 800) {
  if (!frameBuffer || frameBuffer.byteLength < 2) return false;
  const samples = new Int16Array(frameBuffer);
  if (!samples.length) return false;
  let peak = 0;
  for (let i = 0; i < samples.length; i++) {
    const amp = Math.abs(samples[i]);
    if (amp > peak) peak = amp;
  }
  return peak > peakThreshold;
}

/** PCM s16le mono → WAV ArrayBuffer */
export function pcmToWav(pcmBuffer, sampleRate = 16000) {
  const pcm =
    pcmBuffer instanceof ArrayBuffer ? new Uint8Array(pcmBuffer) : pcmBuffer;
  const dataLength = pcm.byteLength;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  const writeStr = (offset, str) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, dataLength, true);
  new Uint8Array(buffer, 44).set(pcm);

  return buffer;
}

/** 合并多个 PCM ArrayBuffer */
export function mergeArrayBuffers(buffers) {
  const total = buffers.reduce((sum, b) => sum + b.byteLength, 0);
  const merged = new Uint8Array(total);
  let offset = 0;
  for (const buf of buffers) {
    merged.set(new Uint8Array(buf), offset);
    offset += buf.byteLength;
  }
  return merged.buffer;
}
