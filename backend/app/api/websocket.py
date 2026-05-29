"""
语音 WebSocket 主接口 — `/ws/voice`。

功能：
1. 接收 text.message 文本消息，直接交给 Agent 处理。
2. 接收 audio.chunk 音频分片（base64 PCM），累积到缓冲区。
3. 收到 audio.end 后，调用 ASR 服务转录，再将文本交给 Agent。
4. Agent 处理完成后，推送 agent.reply、tts.chunk、turn.done 给前端。
5. 连接断开或异常时清理会话资源。

协议说明（当前后端实际协议，纯 JSON，无二进制 header）：
    客户端 → 服务端: text.message / audio.chunk / audio.end
    服务端 → 客户端: transcription / agent.reply / tts.chunk / turn.done / error
"""

import asyncio
import base64
import json
import logging
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.database import get_session_factory
from app.schemas.ws_schema import AgentReply, ErrorMessage, TTSChunkMessage, TranscriptionResult, TurnDone
from app.services.agent_service import CalendarAgentService
from app.services.asr_service import get_asr_service
from app.services.session_service import session_service
from app.services.tts_service import get_tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])
PCM_STREAM_CHUNK_BYTES = 14400


def _safe_text(text: str, max_len: int = 200) -> str:
    """截断过长文本，避免日志输出过大。"""
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len] + "...[已截断]"


@router.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    """
    语音 WebSocket 主入口。

    完整处理链路：
        text.message / audio.chunk → ASR转录 → Agent处理 →
        agent.reply → tts.chunk → turn.done

    Args:
        ws: FastAPI WebSocket 连接对象。
    """
    await ws.accept()
    session_id = None
    user_id = ws.query_params.get("user_id", "demo_user")
    agent_service = CalendarAgentService()
    asr = get_asr_service()
    tts = get_tts_service()
    audio_buffer: list[bytes] = []
    recording_meta: dict[str, object] = {}

    client_info = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    logger.info("[WebSocket] 连接已建立 client=%s", client_info)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("[WebSocket] 收到非法 JSON 消息")
                await ws.send_json(ErrorMessage(message="invalid json").model_dump())
                continue

            msg_type = msg.get("type")

            if msg_type == "text.message":
                session_id = msg.get("session_id", "unknown")
                user_id = msg.get("user_id", user_id) or "demo_user"
                text = msg.get("text", "")
                if not text:
                    logger.warning("[WebSocket] 收到空文本消息 session_id=%s", session_id)
                    await ws.send_json(ErrorMessage(message="empty text").model_dump())
                    continue

                logger.info(
                    "[WebSocket] 收到文本消息 session_id=%s 文本=%s",
                    session_id,
                    _safe_text(text),
                )
                await session_service.register(session_id, user_id=user_id)
                await _process_text(ws, agent_service, tts, user_id, session_id, text)

            elif msg_type == "audio_start":
                session_id = msg.get("session_id", "unknown")
                user_id = msg.get("user_id", user_id) or "demo_user"
                await session_service.register(session_id, user_id=user_id)
                audio_buffer.clear()
                recording_meta = {
                    "format": msg.get("format", ""),
                    "sample_rate": msg.get("sampleRate", msg.get("sample_rate", "")),
                }
                logger.info(
                    "[WebSocket] 音频开始 session_id=%s format=%s sample_rate=%s",
                    session_id,
                    recording_meta["format"],
                    recording_meta["sample_rate"],
                )

            elif msg_type == "audio.chunk":
                session_id = msg.get("session_id", "unknown")
                user_id = msg.get("user_id", user_id) or "demo_user"
                await session_service.register(session_id, user_id=user_id)
                try:
                    chunk = base64.b64decode(msg.get("data", ""))
                except Exception:
                    logger.warning(
                        "[WebSocket] 收到非法 base64 音频数据 session_id=%s", session_id
                    )
                    await ws.send_json(
                        ErrorMessage(message="invalid base64 audio data").model_dump()
                    )
                    continue

                chunk_size = len(chunk)
                audio_buffer.append(chunk)

                if chunk_size == 0:
                    logger.debug("[WebSocket] 收到空音频分片 session_id=%s", session_id)
                elif chunk_size > 128 * 1024:
                    logger.warning(
                        "[WebSocket] 收到异常大的音频分片 session_id=%s 分片大小=%s字节",
                        session_id,
                        chunk_size,
                    )
                else:
                    logger.debug(
                        "[WebSocket] 收到音频分片 session_id=%s 分片大小=%s字节 累计=%s片",
                        session_id,
                        chunk_size,
                        len(audio_buffer),
                    )

            elif msg_type in ("audio.end", "audio_end"):
                session_id = msg.get("session_id", "unknown")
                user_id = msg.get("user_id", user_id) or "demo_user"
                await session_service.register(session_id, user_id=user_id)
                sample_rate = msg.get("sample_rate", 16000)
                total_bytes = sum(len(c) for c in audio_buffer)
                logger.info(
                    "[WebSocket] 音频录制结束 session_id=%s 分片数=%s 总字节=%s 采样率=%s",
                    session_id,
                    len(audio_buffer),
                    total_bytes,
                    sample_rate,
                )

                try:
                    text = await asr.transcribe(audio_buffer, sample_rate=sample_rate)
                except Exception as e:
                    logger.exception("[WebSocket] ASR 转录失败 session_id=%s", session_id)
                    await ws.send_json(
                        ErrorMessage(message=f"asr error: {str(e)}").model_dump()
                    )
                    await ws.send_json(TurnDone(success=False).model_dump())
                    audio_buffer.clear()
                    continue

                audio_buffer.clear()

                if not text:
                    logger.warning("[WebSocket] ASR 转录结果为空 session_id=%s", session_id)
                    await ws.send_json(
                        ErrorMessage(message="empty transcription").model_dump()
                    )
                    continue

                logger.info(
                    "[WebSocket] ASR 转录完成 session_id=%s 文本=%s",
                    session_id,
                    _safe_text(text),
                )
                await ws.send_json(TranscriptionResult(text=text).model_dump())
                await _process_text(ws, agent_service, tts, user_id, session_id, text)

            else:
                logger.warning(
                    "[WebSocket] 收到未知消息类型 session_id=%s type=%s",
                    session_id,
                    msg_type,
                )
                await ws.send_json(
                    ErrorMessage(message=f"unknown message type: {msg_type}").model_dump()
                )

    except WebSocketDisconnect:
        logger.info("[WebSocket] 连接正常关闭 session_id=%s", session_id)
    except Exception:
        logger.exception("[WebSocket] 处理过程中发生异常 session_id=%s", session_id)
    finally:
        if session_id:
            await session_service.set_state(session_id, connected=False)
        try:
            await ws.close()
        except Exception:
            pass
        logger.info("[WebSocket] 连接资源已清理，短期记忆保留至 TTL 过期 session_id=%s", session_id)


async def _process_text(
    ws: WebSocket,
    agent_service: CalendarAgentService,
    tts,
    user_id: str,
    session_id: str,
    text: str,
):
    """
    处理用户文本：调用 Agent → 推送回复 → 合成 TTS 音频。

    流程：
        1. 调用 CalendarAgentService.handle_text() 获取 reply_text 和 speech。
        2. 推送 agent.reply 文本消息。
        3. 优先使用 Agent 原生 TTS 音频（speech），不可用时 fallback 独立 TTS。
        4. 推送 turn.done 表示本轮处理结束。

    Args:
        ws: WebSocket 连接对象。
        agent_service: CalendarAgentService 实例。
        tts: 独立 TTS 服务（fallback 用）。
        session_id: 会话 ID。
        text: 用户文本或 ASR 转录文本。
    """
    async with get_session_factory()() as db:
        try:
            async def _forward_streamed_speech(chunk: bytes, is_last: bool) -> None:
                await _send_pcm_chunks_as_tts_messages(
                    ws=ws,
                    pcm_blocks=[chunk],
                    session_id=session_id,
                    final_is_last=is_last,
                )

            result = await agent_service.handle_text(
                db=db,
                user_id=user_id,
                session_id=session_id,
                text=text,
                on_speech_chunk=_forward_streamed_speech,
            )
        except Exception as exc:
            logger.exception("[WebSocket] Agent 处理失败 session_id=%s", session_id)
            await ws.send_json(
                ErrorMessage(message=f"agent error: {str(exc)}").model_dump()
            )
            await ws.send_json(TurnDone(success=False).model_dump())
            return

    reply_text = result["reply_text"]
    speech = result.get("speech")
    speech_streamed = result.get("speech_streamed", False)
    need_confirm = result.get("need_confirm", False)

    logger.info(
        "[WebSocket] Agent 回复 session_id=%s 文本=%s need_confirm=%s",
        session_id,
        _safe_text(reply_text),
        need_confirm,
    )

    await ws.send_json(AgentReply(text=reply_text, need_confirm=need_confirm).model_dump())

    if speech_streamed:
        logger.info("[WebSocket] Agent 原生 TTS 已实时推送 session_id=%s", session_id)
    elif speech is not None:
        speech_size = sum(len(c) for c in speech)
        logger.info(
            "[WebSocket] 使用 Agent 原生 TTS 音频 session_id=%s 分片数=%s 总字节=%s",
            session_id,
            len(speech),
            speech_size,
        )
        await _send_pcm_chunks_as_tts_messages(
            ws=ws,
            pcm_blocks=speech,
            session_id=session_id,
            final_is_last=True,
        )
    else:
        logger.info("[WebSocket] Agent 未返回音频，启用 TTS 兜底 session_id=%s", session_id)
        await _send_standalone_tts_chunks(ws, tts, reply_text)

    logger.info("[WebSocket] 本轮处理完成 session_id=%s", session_id)
    await ws.send_json(TurnDone(success=True).model_dump())


async def _send_pcm_chunks_as_tts_messages(
    ws: WebSocket,
    pcm_blocks,
    session_id: str,
    final_is_last: bool,
):
    """
    将 PCM 音频块切分成多个 `tts.chunk` 消息并推送给前端。

    Args:
        ws: WebSocket 连接对象。
        pcm_blocks: PCM 音频块集合。
        session_id: 当前会话 ID。
        final_is_last: 当前这批 PCM 是否代表整段音频的最后一批。
    """
    audio_blocks = pcm_blocks if isinstance(pcm_blocks, list) else [pcm_blocks]
    pcm_chunks: list[bytes] = []
    for block in audio_blocks:
        audio_bytes = block if isinstance(block, bytes) else bytes(block)
        if not audio_bytes:
            continue
        for start in range(0, len(audio_bytes), PCM_STREAM_CHUNK_BYTES):
            pcm_chunks.append(audio_bytes[start:start + PCM_STREAM_CHUNK_BYTES])

    if not pcm_chunks:
        pcm_chunks.append(b"")

    total = len(pcm_chunks)
    for i, chunk in enumerate(pcm_chunks):
        is_last = final_is_last and (i == total - 1)
        encoded = base64.b64encode(chunk).decode()
        logger.debug(
            "[WebSocket] 发送 TTS 分片 session_id=%s 序号=%s/%s 大小=%s字节 是否结束=%s",
            session_id,
            i + 1,
            total,
            len(chunk),
            is_last,
        )
        await ws.send_json(TTSChunkMessage(data=encoded, is_last=is_last).model_dump())
        await asyncio.sleep(0)


async def _send_agent_speech_as_tts_chunk(ws: WebSocket, speech):
    """
    将 ReActAgent 原生 TTS 返回的 PCM 音频分片，转为 tts.chunk 推送给前端。

    当前 AgentScope v1.0 通过 post_print hook 捕获的 speech 是 list[bytes]，
    每个元素是已解码的 PCM 音频数据。

    Args:
        ws: WebSocket 连接对象。
        speech: AgentScope 捕获的音频数据（list[bytes]）。
    """
    try:
        await _send_pcm_chunks_as_tts_messages(
            ws=ws,
            pcm_blocks=speech,
            session_id="agent",
            final_is_last=True,
        )
        logger.info("[WebSocket] TTS 音频推送完成 分片数=%s", len(speech) if isinstance(speech, list) else 1)
    except Exception:
        logger.exception("[WebSocket] 推送 Agent TTS 音频失败")


async def _send_standalone_tts_chunks(ws: WebSocket, tts, text: str):
    """
    Fallback：通过独立 DashScopeTTSService 合成语音并推送 tts.chunk。

    仅在 ReActAgent 未返回 speech 时使用。

    Args:
        ws: WebSocket 连接对象。
        tts: 独立 TTS 服务实例。
        text: 需要合成的文本。
    """
    try:
        chunks = await tts.synthesize(text)
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            encoded = base64.b64encode(chunk.audio_data).decode()
            logger.debug(
                "[WebSocket] 发送 TTS 分片(fallback) 序号=%s/%s 大小=%s字节 是否结束=%s",
                i + 1,
                total,
                len(chunk.audio_data),
                chunk.is_last,
            )
            await ws.send_json(
                TTSChunkMessage(data=encoded, is_last=chunk.is_last).model_dump()
            )
        logger.info("[WebSocket] TTS 音频推送完成(fallback) 分片数=%s", total)
    except Exception:
        logger.exception("[WebSocket] Fallback TTS 推送失败")
