from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.asr_service import DashScopeASRService, _extract_text_from_sentence


def test_extract_text_from_sentence_supports_list_payload():
    sentence = [
        {"text": "明天"},
        {"text": "下午三点"},
        {"text": "提醒我开组会"},
    ]

    assert _extract_text_from_sentence(sentence) == "明天下午三点提醒我开组会"


@pytest.mark.asyncio
@patch("app.services.asr_service.Recognition")
async def test_transcribe_uses_sync_recognition_result(mock_recognition_cls):
    mock_result = SimpleNamespace(
        get_sentence=lambda: [{"text": "明天下午三点提醒我开组会"}]
    )
    mock_recognition = mock_recognition_cls.return_value
    mock_recognition.call.return_value = mock_result

    service = DashScopeASRService(api_key="test-key")
    text = await service.transcribe([b"\x00\x01" * 8000], sample_rate=16000)

    assert text == "明天下午三点提醒我开组会"
