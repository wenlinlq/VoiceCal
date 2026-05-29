"""
ASR 语音识别服务。

当前实现：DashScope paraformer-realtime-v2（文件级同步识别）。
收到 audio.end 后将累积的 PCM 音频写入临时 WAV，调用 DashScope Recognition API 转录。

未来升级方向：改为 real-time 流式识别，边收音频边出 partial 结果。
"""

import asyncio
import logging
import tempfile
import wave
from abc import ABC, abstractmethod
from typing import Optional

from dashscope.audio.asr.recognition import Recognition, RecognitionCallback, RecognitionResult

from app.core.config import settings

logger = logging.getLogger(__name__)


class ASRService(ABC):
    """ASR 服务抽象基类。"""

    @abstractmethod
    async def transcribe(self, audio_chunks: list[bytes], sample_rate: int = 16000) -> str:
        """将音频分片列表转录为文本。"""
        ...


class _Collector(RecognitionCallback):
    """DashScope ASR 结果收集器。"""

    def __init__(self):
        self.sentences: list[str] = []
        self.error_msg: Optional[str] = None

    def on_open(self):
        pass

    def on_event(self, result: RecognitionResult):
        sentence = result.get_sentence()
        if sentence and "text" in sentence:
            text = sentence["text"].strip()
            if text:
                self.sentences.append(text)

    def on_complete(self):
        pass

    def on_error(self, result: RecognitionResult):
        self.error_msg = result.message

    def on_close(self):
        pass


def _extract_text_from_sentence(sentence) -> str:
    """从 DashScope sentence 结构中尽量提取可用文本。"""
    if not sentence:
        return ""

    if isinstance(sentence, dict):
        for key in ("text", "sentence", "transcript"):
            value = sentence.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    if isinstance(sentence, list):
        parts = [_extract_text_from_sentence(item) for item in sentence]
        return "".join(part for part in parts if part)

    if isinstance(sentence, str):
        return sentence.strip()

    return ""


class DashScopeASRService(ASRService):
    """基于 DashScope paraformer-realtime-v2 的 ASR 服务。

    工作方式：
        1. 将 audio_chunks 列表合并，写入临时 WAV 文件。
        2. 调用 DashScope Recognition API（文件级同步识别）。
        3. 返回转录文本。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.dashscope_api_key

    async def transcribe(self, audio_chunks: list[bytes], sample_rate: int = 16000) -> str:
        """
        将累积的音频分片转录为文本。

        Args:
            audio_chunks: PCM 音频分片列表（16bit / mono）。
            sample_rate: 音频采样率，默认 16000Hz，前端可传真实值。

        Returns:
            str: 转录后的文本，失败或无声时返回空字符串。
        """
        if not audio_chunks:
            logger.warning("[ASR] 音频分片为空，跳过转录")
            return ""

        total_bytes = sum(len(c) for c in audio_chunks)
        logger.info(
            "[ASR] 开始转录 分片数=%s 总字节=%s 采样率=%sHz 模型=paraformer-realtime-v2",
            len(audio_chunks),
            total_bytes,
            sample_rate,
        )

        raw = b"".join(audio_chunks)

        # 将原始 PCM 重采样到 16kHz（DashScope ASR 最佳识别采样率）
        if sample_rate != 16000:
            import numpy as np
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            # 简单线性重采样：计算目标采样点数
            target_len = int(len(audio_np) * 16000 / sample_rate)
            indices = np.linspace(0, len(audio_np) - 1, target_len)
            resampled = np.interp(indices, np.arange(len(audio_np)), audio_np)
            raw = resampled.astype(np.int16).tobytes()
            logger.info(
                "[ASR] 重采样 %sHz→16000Hz 原始采样点=%s 目标采样点=%s",
                sample_rate, len(audio_np), target_len,
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(raw)
            tmp_path = f.name

        # 调试：保存最近一次 WAV 文件，方便验证音频是否有效
        debug_path = "/tmp/voicecal_last_asr.wav"
        try:
            import shutil
            shutil.copy(tmp_path, debug_path)
            logger.info("[ASR] 调试音频已保存: %s", debug_path)
        except Exception:
            pass

        try:
            collector = _Collector()
            rec = Recognition(
                model="paraformer-realtime-v2",
                callback=collector,
                format="wav",
                sample_rate=16000,
                api_key=self.api_key,
            )

            def _run():
                return rec.call(file=tmp_path)

            result = await asyncio.to_thread(_run)

            result_code = getattr(result, "code", None)
            result_message = getattr(result, "message", None)
            if result_code and result_code != "Success":
                logger.error(
                    "[ASR] 上游返回错误 code=%s message=%s request_id=%s",
                    result_code,
                    result_message,
                    getattr(result, "request_id", None),
                )
                raise RuntimeError(f"[{result_code}] {result_message}")

            if collector.error_msg:
                logger.error("[ASR] 转录失败 错误=%s", collector.error_msg)
                raise RuntimeError(collector.error_msg)

            sentence = result.get_sentence()
            logger.debug("[ASR] 原始返回 sentence=%s raw=%s", sentence, result)

            full_text = _extract_text_from_sentence(sentence)
            if not full_text:
                full_text = "".join(collector.sentences)
                logger.warning(
                    "[ASR] 未从同步结果中提取到文本 sentence=%s callback_sentences=%s",
                    sentence,
                    collector.sentences,
                )
            logger.info(
                "[ASR] 转录完成 文本=%s 句子数=%s",
                full_text.strip() or "(空)",
                len(sentence or []) if isinstance(sentence, list) else int(bool(full_text)),
            )
            return full_text.strip()
        except Exception:
            logger.exception("[ASR] 转录过程异常")
            raise
        finally:
            import os
            os.unlink(tmp_path)


def get_asr_service() -> ASRService:
    """获取 ASR 服务实例（工厂函数）。"""
    return DashScopeASRService()
