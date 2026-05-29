import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.tts_service import TTSChunk


@pytest.fixture(scope="module")
def ws_client():
    with TestClient(app) as client:
        yield client


def _mock_agent_result(reply_text="ok"):
    return {
        "reply_text": reply_text,
        "speech": None,
        "raw_msg": None,
    }


def _mock_tts():
    mock = MagicMock()
    mock.synthesize = AsyncMock(return_value=[TTSChunk(audio_data=b"\x00" * 100, is_last=True)])
    return mock


def _mock_asr():
    mock = MagicMock()
    mock.transcribe = AsyncMock(return_value="明天下午三点提醒我开组会")
    return mock


@patch("app.api.websocket.get_tts_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_text_message(mock_agent_cls, mock_factory, mock_tts_fn, ws_client):
    mock_agent = MagicMock()
    mock_agent.handle_text = AsyncMock(return_value=_mock_agent_result(
        reply_text="好的，已为你添加日程"
    ))
    mock_agent_cls.return_value = mock_agent
    mock_tts_fn.return_value = _mock_tts()

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "text.message",
            "session_id": "sess_demo",
            "text": "明天下午三点提醒我开组会",
        }))

        reply = json.loads(ws.receive_text())
        assert reply["type"] == "agent.reply"
        assert "已为你添加" in reply["text"]

        tts = json.loads(ws.receive_text())
        assert tts["type"] == "tts.chunk"
        assert tts["is_last"] is True

        done = json.loads(ws.receive_text())
        assert done["type"] == "turn.done"
        assert done["success"] is True


@patch("app.api.websocket.get_tts_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_text_message_splits_large_agent_tts_chunks(mock_agent_cls, mock_factory, mock_tts_fn, ws_client):
    mock_agent = MagicMock()
    mock_agent.handle_text = AsyncMock(return_value={
        "reply_text": "你好，有什么可以帮你的吗？",
        "speech": [b"\x01\x02" * 9000],
        "raw_msg": None,
    })
    mock_agent_cls.return_value = mock_agent
    mock_tts_fn.return_value = _mock_tts()

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "text.message",
            "session_id": "sess_demo_stream",
            "text": "你好",
        }))

        reply = json.loads(ws.receive_text())
        assert reply["type"] == "agent.reply"

        first_tts = json.loads(ws.receive_text())
        second_tts = json.loads(ws.receive_text())
        assert first_tts["type"] == "tts.chunk"
        assert second_tts["type"] == "tts.chunk"
        assert first_tts["is_last"] is False
        assert second_tts["is_last"] is True

        done = json.loads(ws.receive_text())
        assert done["type"] == "turn.done"
        assert done["success"] is True


@patch("app.api.websocket.get_tts_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_text_message_streams_agent_tts_in_real_time(mock_agent_cls, mock_factory, mock_tts_fn, ws_client):
    async def _handle_text(**kwargs):
        on_speech_chunk = kwargs["on_speech_chunk"]
        await on_speech_chunk(b"\x01\x02" * 9000, False)
        await on_speech_chunk(b"\x03\x04" * 10, True)
        return {
            "reply_text": "你好呀",
            "speech": None,
            "speech_streamed": True,
            "need_confirm": False,
            "raw_msg": None,
        }

    mock_agent = MagicMock()
    mock_agent.handle_text = AsyncMock(side_effect=_handle_text)
    mock_agent_cls.return_value = mock_agent
    mock_tts = _mock_tts()
    mock_tts_fn.return_value = mock_tts

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "text.message",
            "session_id": "sess_demo_realtime_stream",
            "text": "你好",
        }))

        first_tts = json.loads(ws.receive_text())
        second_tts = json.loads(ws.receive_text())
        third_tts = json.loads(ws.receive_text())
        reply = json.loads(ws.receive_text())
        done = json.loads(ws.receive_text())

        assert first_tts["type"] == "tts.chunk"
        assert second_tts["type"] == "tts.chunk"
        assert third_tts["type"] == "tts.chunk"
        assert first_tts["is_last"] is False
        assert second_tts["is_last"] is False
        assert third_tts["is_last"] is True

        assert base64.b64decode(first_tts["data"]) == (b"\x01\x02" * 7200)
        assert base64.b64decode(second_tts["data"]) == (b"\x01\x02" * 1800)
        assert base64.b64decode(third_tts["data"]) == (b"\x03\x04" * 10)

        assert reply["type"] == "agent.reply"
        assert reply["text"] == "你好呀"

        assert done["type"] == "turn.done"
        assert done["success"] is True
        mock_tts.synthesize.assert_not_awaited()


@patch("app.api.websocket.get_tts_service")
@patch("app.api.websocket.get_asr_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_audio_end_to_end(mock_agent_cls, mock_factory, mock_asr_fn, mock_tts_fn, ws_client):
    mock_agent = MagicMock()
    mock_agent.handle_text = AsyncMock(return_value=_mock_agent_result(
        reply_text="好的，已为你添加日程。"
    ))
    mock_agent_cls.return_value = mock_agent
    mock_tts_fn.return_value = _mock_tts()
    mock_asr_fn.return_value = _mock_asr()

    fake_audio = base64.b64encode(b"fake audio bytes").decode()

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "audio.chunk",
            "session_id": "sess_demo",
            "data": fake_audio,
        }))
        ws.send_text(json.dumps({
            "type": "audio.chunk",
            "session_id": "sess_demo",
            "data": fake_audio,
        }))
        ws.send_text(json.dumps({
            "type": "audio.end",
            "session_id": "sess_demo",
        }))

        tr = json.loads(ws.receive_text())
        assert tr["type"] == "transcription"
        assert "开组会" in tr["text"]

        reply = json.loads(ws.receive_text())
        assert reply["type"] == "agent.reply"

        tts = json.loads(ws.receive_text())
        assert tts["type"] == "tts.chunk"

        done = json.loads(ws.receive_text())
        assert done["type"] == "turn.done"
        assert done["success"] is True


def test_invalid_json(ws_client):
    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text("not json")
        reply = json.loads(ws.receive_text())
        assert reply["type"] == "error"
        assert "invalid json" in reply["message"]


def test_empty_text(ws_client):
    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "text.message",
            "session_id": "sess1",
            "text": "",
        }))
        reply = json.loads(ws.receive_text())
        assert reply["type"] == "error"
        assert "empty text" in reply["message"]


def test_unknown_message_type(ws_client):
    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "weird.type",
            "session_id": "sess1",
        }))
        reply = json.loads(ws.receive_text())
        assert reply["type"] == "error"
        assert "unknown" in reply["message"]


def test_audio_invalid_base64(ws_client):
    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "audio.chunk",
            "session_id": "sess1",
            "data": "!!!not-valid-base64!!!",
        }))
        reply = json.loads(ws.receive_text())
        assert reply["type"] == "error"
        assert "base64" in reply["message"]


@patch("app.api.websocket.get_asr_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_audio_end_surfaces_asr_error(mock_agent_cls, mock_factory, mock_asr_fn, ws_client):
    mock_agent_cls.return_value = MagicMock()
    mock_asr = MagicMock()
    mock_asr.transcribe = AsyncMock(side_effect=RuntimeError("[Arrearage] Access denied"))
    mock_asr_fn.return_value = mock_asr

    fake_audio = base64.b64encode(b"fake audio bytes").decode()

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "audio.chunk",
            "session_id": "sess_demo",
            "data": fake_audio,
        }))
        ws.send_text(json.dumps({
            "type": "audio.end",
            "session_id": "sess_demo",
        }))

        error = json.loads(ws.receive_text())
        assert error["type"] == "error"
        assert "Arrearage" in error["message"]

        done = json.loads(ws.receive_text())
        assert done["type"] == "turn.done"
        assert done["success"] is False


@patch("app.api.websocket.get_tts_service")
@patch("app.api.websocket.get_session_factory")
@patch("app.api.websocket.CalendarAgentService")
def test_text_message_surfaces_agent_error(mock_agent_cls, mock_factory, mock_tts_fn, ws_client):
    mock_agent = MagicMock()
    mock_agent.handle_text = AsyncMock(side_effect=RuntimeError("[Arrearage] Access denied"))
    mock_agent_cls.return_value = mock_agent
    mock_tts_fn.return_value = _mock_tts()

    with ws_client.websocket_connect("/ws/voice") as ws:
        ws.send_text(json.dumps({
            "type": "text.message",
            "session_id": "sess_demo",
            "text": "你好",
        }))

        error = json.loads(ws.receive_text())
        assert error["type"] == "error"
        assert "Arrearage" in error["message"]

        done = json.loads(ws.receive_text())
        assert done["type"] == "turn.done"
        assert done["success"] is False
