"""
TTS 语音合成服务（Fallback 路径）。

    当前实现：DashScope qwen-tts，通过 SpeechSynthesizer 回调式合成 PCM。
仅在 ReActAgent 原生 TTS 不可用时作为兜底使用。

主路径 TTS 由 AgentScope ReActAgent(tts_model=...) 原生提供，
通过 app/services/agent_service.py 的 post_print hook 捕获 speech 音频。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from dashscope.audio.tts import ResultCallback, SpeechSynthesizer

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TTSChunk:
    """TTS 音频分片。"""
    audio_data: bytes
    is_last: bool = False


class TTSService(ABC):
    """TTS 服务抽象基类。"""

    @abstractmethod
    async def synthesize(self, text: str) -> list[TTSChunk]:
        """将文本合成为语音，返回音频分片列表。"""
        ...


class _ChunkCollector(ResultCallback):
    """DashScope SpeechSynthesizer 回调收集器。

    在回调中收集每个音频帧，on_complete 时标记最后一个分片。
    """

    def __init__(self):
        self.chunks: list[TTSChunk] = []

    def on_open(self):
        pass

    def on_event(self, result):
        audio = result.get_audio_frame()
        if audio is not None:
            self.chunks.append(TTSChunk(audio_data=audio))

    def on_complete(self):
        if self.chunks:
            self.chunks[-1].is_last = True
        else:
            self.chunks.append(TTSChunk(audio_data=b"", is_last=True))

    def on_close(self):
        pass

    def on_error(self, result):
        logger.error("[TTS] 合成出错 错误=%s", result.message)


class DashScopeTTSService(TTSService):
    """
    Fallback TTS 服务：独立调用 DashScope SpeechSynthesizer。

    仅在 ReActAgent 未返回 speech 时由 WebSocket 层调用。
    模型：qwen-tts，输出 PCM 格式。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.dashscope_api_key

    async def synthesize(self, text: str) -> list[TTSChunk]:
        """
        将文本合成为语音分片列表。

        Args:
            text: 要合成的文本内容。

        Returns:
            list[TTSChunk]: 音频分片列表，最后一个分片 is_last=True。
        """
        logger.info("[TTS] 开始语音合成(fallback) 文本长度=%s 模型=qwen-tts", len(text))

        collector = _ChunkCollector()

        def _run():
            SpeechSynthesizer.call(
                model="qwen-tts",
                text=text,
                api_key=self.api_key,
                format="pcm",
                callback=collector,
            )

        await asyncio.to_thread(_run)

        total_bytes = sum(len(c.audio_data) for c in collector.chunks)
        logger.info(
            "[TTS] 语音合成完成(fallback) 分片数=%s 总音频大小=%s字节",
            len(collector.chunks),
            total_bytes,
        )
        return collector.chunks


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例（工厂函数）。"""
    return DashScopeTTSService()
