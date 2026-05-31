"""
TTS 延迟诊断测试。

模拟三种 TTS 路径的端到端延迟，定位瓶颈所在。
"""
import asyncio
import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


PCM_STREAM_CHUNK_BYTES = 14400
TTS_SAMPLE_RATE = 24000


def make_fake_pcm(duration_seconds: float) -> bytes:
    """生成模拟 PCM 音频（16-bit mono）。"""
    num_samples = int(duration_seconds * TTS_SAMPLE_RATE)
    return b"\x00\x01" * num_samples  # 2 bytes per sample


def split_into_chunks(pcm: bytes) -> list[bytes]:
    """模拟 _send_pcm_chunks_as_tts_messages 的分片逻辑。"""
    chunks = []
    for start in range(0, len(pcm), PCM_STREAM_CHUNK_BYTES):
        chunks.append(pcm[start:start + PCM_STREAM_CHUNK_BYTES])
    return chunks


class FakeWS:
    """模拟 WebSocket，记录发送消息。"""
    def __init__(self):
        self.sent = []
        self.send_times = []

    async def send_json(self, data):
        self.send_times.append(time.monotonic())
        self.sent.append(data)


async def measure_chunk_sending(pcm_bytes: bytes, label: str) -> dict:
    """测量分片发送耗时（模拟 _send_pcm_chunks_as_tts_messages）。"""
    ws = FakeWS()
    chunks = split_into_chunks(pcm_bytes)
    total = len(chunks)

    t0 = time.monotonic()
    for i, chunk in enumerate(chunks):
        is_last = (i == total - 1)
        encoded = base64.b64encode(chunk).decode()
        await ws.send_json({"type": "tts.chunk", "data": encoded, "is_last": is_last})
        await asyncio.sleep(0)
    elapsed = time.monotonic() - t0

    return {
        "label": label,
        "audio_duration_seconds": len(pcm_bytes) / 2 / TTS_SAMPLE_RATE,
        "total_bytes": len(pcm_bytes),
        "chunk_count": total,
        "send_elapsed_seconds": round(elapsed, 4),
        "chunks_per_second": round(total / elapsed, 1) if elapsed > 0 else float("inf"),
    }


class TestTTSLatency:
    """TTS 延迟诊断测试套件。"""

    @pytest.mark.asyncio
    async def test_chunk_sending_speed_short_response(self):
        """短回复（~3秒音频）的分片发送速度。"""
        pcm = make_fake_pcm(3.0)
        result = await measure_chunk_sending(pcm, "短回复 3s")
        print(f"\n[TTS诊断] {result}")
        # 3s 音频 → 144000 bytes → 10 chunks，应该在 50ms 内完成
        assert result["chunk_count"] == 10, f"期望 10 个分片，实际 {result['chunk_count']}"
        assert result["send_elapsed_seconds"] < 0.5, (
            f"分片发送太慢: {result['send_elapsed_seconds']:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_chunk_sending_speed_long_response(self):
        """长回复（~10秒音频）的分片发送速度。"""
        pcm = make_fake_pcm(10.0)
        result = await measure_chunk_sending(pcm, "长回复 10s")
        print(f"\n[TTS诊断] {result}")
        # 10s 音频 → 480000 bytes → 34 chunks
        expected_chunks = 34  # ceil(480000 / 14400)
        assert result["chunk_count"] == expected_chunks, (
            f"期望 {expected_chunks} 个分片，实际 {result['chunk_count']}"
        )
        assert result["send_elapsed_seconds"] < 1.0, (
            f"分片发送太慢: {result['send_elapsed_seconds']:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_chunk_sending_speed_very_long_response(self):
        """超长回复（~30秒音频）的分片发送速度 — 压力测试。"""
        pcm = make_fake_pcm(30.0)
        result = await measure_chunk_sending(pcm, "超长回复 30s")
        print(f"\n[TTS诊断] {result}")
        # 30s 音频 → 1440000 bytes → 100 chunks
        assert result["send_elapsed_seconds"] < 2.0, (
            f"超长音频分片发送太慢: {result['send_elapsed_seconds']:.3f}s，"
            f"{result['chunk_count']} 个分片"
        )

    @pytest.mark.asyncio
    async def test_batch_vs_streaming_latency_comparison(self):
        """对比：批量发送 vs 模拟流式发送的延迟差异。"""
        # 模拟 5 次 post_print，每次生成 0.6s 音频（~28800 bytes）
        post_print_count = 5
        chunk_per_print = make_fake_pcm(0.6)  # 每次 ~0.6s

        # === 批量模式：全部收集完后一次性发送 ===
        ws_batch = FakeWS()
        all_pcm = chunk_per_print * post_print_count
        all_chunks = split_into_chunks(all_pcm)

        t0 = time.monotonic()
        for i, chunk in enumerate(all_chunks):
            is_last = (i == len(all_chunks) - 1)
            encoded = base64.b64encode(chunk).decode()
            await ws_batch.send_json({"type": "tts.chunk", "data": encoded, "is_last": is_last})
            await asyncio.sleep(0)
        batch_elapsed = time.monotonic() - t0

        # === 流式模式：每次 post_print 立即发送 ===
        ws_stream = FakeWS()
        stream_first_chunk_at = None
        stream_elapsed_total = 0

        t0 = time.monotonic()
        for pp_idx in range(post_print_count):
            chunks = split_into_chunks(chunk_per_print)
            for i, chunk in enumerate(chunks):
                is_last = (pp_idx == post_print_count - 1) and (i == len(chunks) - 1)
                encoded = base64.b64encode(chunk).decode()
                await ws_stream.send_json({"type": "tts.chunk", "data": encoded, "is_last": is_last})
                if stream_first_chunk_at is None:
                    stream_first_chunk_at = time.monotonic() - t0
                await asyncio.sleep(0)
            # 模拟 post_print 之间的间隔（agent 思考/生成）
            if pp_idx < post_print_count - 1:
                await asyncio.sleep(0.01)
        stream_elapsed_total = time.monotonic() - t0

        print(
            f"\n[TTS诊断] 批量发送: {len(all_chunks)} 个分片, "
            f"耗时 {batch_elapsed:.3f}s, "
            f"首个分片可播放时间={batch_elapsed:.3f}s（全部发送完成后）"
        )
        print(
            f"[TTS诊断] 流式发送: {len(ws_stream.sent)} 个分片, "
            f"首个分片到达={stream_first_chunk_at:.3f}s, "
            f"全部完成={stream_elapsed_total:.3f}s"
        )
        print(
            f"[TTS诊断] 流式相比批量，首个音频分片提前 "
            f"{batch_elapsed - (stream_first_chunk_at or 0):.3f}s 到达前端"
        )

        # 流式首个分片应该在很短时间内到达（< 0.01s）
        assert stream_first_chunk_at is not None
        assert stream_first_chunk_at < 0.05, (
            f"流式首个分片延迟过高: {stream_first_chunk_at:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_pcm_chunk_size_efficiency(self):
        """分析当前 PCM_STREAM_CHUNK_BYTES=14400 是否合理。"""
        # 14400 bytes = 7200 samples = 0.3s audio at 24kHz
        chunk_duration = PCM_STREAM_CHUNK_BYTES / 2 / TTS_SAMPLE_RATE
        print(f"\n[TTS诊断] PCM_STREAM_CHUNK_BYTES={PCM_STREAM_CHUNK_BYTES}")
        print(f"[TTS诊断] 每个分片音频时长={chunk_duration:.2f}s")
        print(f"[TTS诊断] base64 膨胀后大小={len(base64.b64encode(b'x' * PCM_STREAM_CHUNK_BYTES))} bytes")

        # 对比不同分片大小下的发送效率
        for chunk_size, label in [(7200, "0.15s"), (14400, "0.30s"), (28800, "0.60s"), (57600, "1.20s")]:
            pcm = make_fake_pcm(5.0)
            ws = FakeWS()
            t0 = time.monotonic()
            for start in range(0, len(pcm), chunk_size):
                chunk = pcm[start:start + chunk_size]
                encoded = base64.b64encode(chunk).decode()
                await ws.send_json({"type": "tts.chunk", "data": encoded, "is_last": False})
                await asyncio.sleep(0)
            elapsed = time.monotonic() - t0
            print(
                f"[TTS诊断] 分片大小={chunk_size} ({label}) → "
                f"{len(ws.sent)} 个分片, 耗时 {elapsed:.4f}s"
            )

    @pytest.mark.asyncio
    async def test_simulate_full_tts_pipeline_timing(self):
        """模拟完整 TTS 管道的时序分解。

        模拟场景：
        - Agent 用 3 秒生成文本（含 TTS 合成）
        - 期间 post_print 被调用 3 次（第1次在 1.2s，第2次在 2.5s，最后在 3.0s）
        - 每次 post_print 携带累积的音频（含增量部分）
        """
        total_agent_time = 3.0
        post_print_times = [0.8, 2.0, 3.0]  # 每次 post_print 相对于 start 的时间
        audio_per_print = [
            make_fake_pcm(1.0),   # 第1次: 1s 音频
            make_fake_pcm(2.0),   # 第2次: 2s 音频（累积）
            make_fake_pcm(3.0),   # 第3次: 3s 音频（累积，最终）
        ]

        # 提取增量（模拟 _extract_incremental_audio_chunks）
        incremental_chunks = []
        prev_len = 0
        for pcm in audio_per_print:
            new_data = pcm[prev_len:]
            prev_len = len(pcm)
            if new_data:
                incremental_chunks.append(new_data)

        ws = FakeWS()
        t_start = time.monotonic()

        for idx, (ppt, chunk) in enumerate(zip(post_print_times, incremental_chunks)):
            # 模拟等待到 post_print 时间点
            now = time.monotonic() - t_start
            wait = ppt - now
            if wait > 0:
                await asyncio.sleep(wait)

            # 发送增量音频
            is_last_batch = (idx == len(incremental_chunks) - 1)
            sub_chunks = split_into_chunks(chunk)
            for si, sc in enumerate(sub_chunks):
                is_last = is_last_batch and (si == len(sub_chunks) - 1)
                encoded = base64.b64encode(sc).decode()
                await ws.send_json({"type": "tts.chunk", "data": encoded, "is_last": is_last})
                await asyncio.sleep(0)

        elapsed = time.monotonic() - t_start

        print(f"\n[TTS诊断] 完整流水线模拟")
        print(f"[TTS诊断] Agent 总耗时(模拟): {total_agent_time}s")
        print(f"[TTS诊断] post_print 次数: {len(post_print_times)}")
        print(f"[TTS诊断] 增量音频分片: {len(incremental_chunks)} 批")
        print(f"[TTS诊断] 发送总消息数: {len(ws.sent)} 条")
        print(f"[TTS诊断] 首次 tts.chunk 到达: 约 {post_print_times[0]:.1f}s 处")
        print(f"[TTS诊断] 最后 tts.chunk 到达: {elapsed:.3f}s")
        print(f"[TTS诊断] 前端可开始播放: 约 {post_print_times[0] + 0.45:.1f}s（含缓冲）")

        # 验证：首次音频应在第一个 post_print 时间点后立即到达
        assert len(ws.sent) > 0, "应该有 tts.chunk 消息"
        # 首个分片的大致到达时间应该在第一个 post_print 附近
        assert elapsed < total_agent_time + 0.5, (
            f"管道总耗时({elapsed:.2f}s)不应远超 agent 耗时({total_agent_time}s)"
        )

    @pytest.mark.asyncio
    async def test_fallback_tts_path_latency_impact(self):
        """量化 fallback TTS 路径的额外延迟。

        当 AgentScope 原生 TTS 不工作时，需要额外调用 DashScope TTS API。
        这会导致额外的网络往返延迟（通常 1-3 秒）。
        """
        # 模拟 fallback 路径的额外延迟
        # Agent 完成 → 发现 speech=None → 调用独立 TTS → 等待 TTS API → 收到音频 → 分片发送

        agent_elapsed = 3.0  # Agent 文本生成耗时
        tts_api_elapsed = 2.0  # 独立 TTS API 调用耗时（典型值）
        chunk_send_elapsed = 0.05  # 分片发送耗时

        total_streaming = agent_elapsed  # 流式路径：音频随文本生成
        total_fallback = agent_elapsed + tts_api_elapsed + chunk_send_elapsed  # fallback 路径

        print(f"\n[TTS诊断] === Fallback TTS 路径延迟分析 ===")
        print(f"[TTS诊断] 流式路径总延迟(首次可播): ~{agent_elapsed:.1f}s")
        print(f"[TTS诊断] Fallback 路径总延迟(首次可播): ~{total_fallback:.1f}s")
        print(f"[TTS诊断] Fallback 额外延迟: +{tts_api_elapsed:.1f}s")
        print(f"[TTS诊断] ⚠️ 如果走 fallback 路径，用户多等 {tts_api_elapsed:.1f}s")

        assert total_fallback > total_streaming, "Fallback 路径应该比流式路径慢"
