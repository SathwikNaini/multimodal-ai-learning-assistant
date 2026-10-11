import pytest
import google
from google.api_core.exceptions import NotFound, ResourceExhausted

from backend.config.settings import settings
from backend.utils.helpers import (
    INVALID_CONTENT_MESSAGE,
    parse_youtube_id,
    validate_content_for_analysis,
    validate_meaningful_content,
)
from backend.utils.exceptions import APIError
from backend.services import gemini_service
from backend.services.gemini_service import normalize_summary_payload, classify_gemini_error, verify_gemini_connection


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "hi",
        "hello",
        "hiii djk ia",
        "abc xyz",
        "test test",
        "12345",
        "ajkldf qwer zxcv",
        "%%% ### @@@",
        "random characters !@#$%^&*()",
    ],
)
def test_rejects_non_meaningful_content(value):
    with pytest.raises(APIError):
        validate_content_for_analysis(value)


def test_accepts_meaningful_paragraph():
    content = (
        "Machine learning is a branch of artificial intelligence that allows computers to learn patterns "
        "from data and improve their performance without being explicitly programmed for every task."
    )
    result = validate_content_for_analysis(content)
    assert isinstance(result, str)
    assert len(result) >= 20


def test_meaningful_content_helper_returns_false_for_invalid_input():
    is_valid, error = validate_meaningful_content("hiii djk ia")
    assert is_valid is False
    assert error == INVALID_CONTENT_MESSAGE


def test_parse_youtube_id_ignores_query_params():
    url = "https://youtu.be/3n-30SzWefA?si=agy-t7dkh_ye1jRo"
    assert parse_youtube_id(url) == "3n-30SzWefA"


def test_normalize_summary_payload_uses_observations_when_summary_missing():
    payload = {
        "main_theme": "Tech news round-up",
        "important_observations": [
            "Apple raised iPhone prices.",
            "Motorola launched a new Signature model."
        ],
        "learning_gaps": [],
        "quiz": [],
    }
    normalized = normalize_summary_payload(payload)
    assert normalized["summary"] == [
        "Apple raised iPhone prices.",
        "Motorola launched a new Signature model."
    ]


def test_classify_gemini_error_prefers_quota_over_not_found():
    message = "429 You exceeded your current quota, please check your plan and billing details."
    status_code, user_message = classify_gemini_error(Exception(message))
    assert status_code == 429
    assert "quota" in user_message.lower()


def test_settings_loads_gemini_model():
    assert settings.GEMINI_MODEL == "gemini-3.6-flash"


def test_actual_analysis_uses_gemini_3_6_flash(monkeypatch):
    captured = {"startup": None, "analysis": None}

    class DummyResponse:
        text = '{"summary":["First point."],"main_theme":"Example theme","important_observations":["Observation"],"major_topics":[],"key_statistics":[],"important_entities":[],"timeline":[],"turning_points":[],"strengths":[],"weaknesses":[],"core_insights":[],"learning_gaps":[],"quiz":[],"final_verdict":"OK","difficulty_level":"Beginner","estimated_reading_time":"1 min","knowledge_score":50}'

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                captured["analysis"] = model
                return DummyResponse()

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    captured["startup"] = verify_gemini_connection()

    result = gemini_service.generate_summary("Machine learning uses data to identify patterns and improve prediction accuracy.", source_type="text")
    assert captured["startup"] is True
    assert captured["analysis"] == "gemini-3.6-flash"
    assert result["summary"] == ["First point."]
    assert "gemini-pro" not in captured["analysis"]
    assert "gemini-2.5-flash" not in captured["analysis"]


def test_generate_summary_stops_after_daily_quota_error(monkeypatch):
    attempts = {"count": 0}

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                attempts["count"] += 1
                raise ResourceExhausted(
                    "429 You exceeded your current quota. "
                    "Quota metric: generativelanguage.googleapis.com/generate_content_free_tier_requests "
                    "Quota ID: GenerateRequestsPerDayPerModel-FreeTier"
                )

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    with pytest.raises(APIError) as exc:
        gemini_service.generate_summary("Example content for testing the summarization service.", source_type="text")

    assert attempts["count"] == 1
    assert exc.value.status_code == 429
    assert exc.value.message == (
        "Gemini daily API quota exceeded for this project. Please wait for the quota to reset or upgrade the Gemini API plan."
    )


def test_generate_summary_retries_on_transient_503_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    class DummyResponse:
        text = '{"summary":["First point."],"main_theme":"Example theme","important_observations":["Observation"],"major_topics":[],"key_statistics":[],"important_entities":[],"timeline":[],"turning_points":[],"strengths":[],"weaknesses":[],"core_insights":[],"learning_gaps":[],"quiz":[],"final_verdict":"OK","difficulty_level":"Beginner","estimated_reading_time":"1 min","knowledge_score":50}'

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise google.api_core.exceptions.ServiceUnavailable("503 This model is currently experiencing high demand. Please try again later.")
                return DummyResponse()

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    result = gemini_service.generate_summary("Machine learning uses data to identify patterns and improve prediction accuracy.", source_type="text")

    assert attempts["count"] == 2
    assert result["summary"] == ["First point."]


def test_generate_summary_retries_on_transient_503_then_succeeds_on_attempt_3(monkeypatch):
    attempts = {"count": 0}

    class DummyResponse:
        text = '{"summary":["Third attempt succeeded."],"main_theme":"Example theme","important_observations":["Observation"],"major_topics":[],"key_statistics":[],"important_entities":[],"timeline":[],"turning_points":[],"strengths":[],"weaknesses":[],"core_insights":[],"learning_gaps":[],"quiz":[],"final_verdict":"OK","difficulty_level":"Beginner","estimated_reading_time":"1 min","knowledge_score":50}'

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                attempts["count"] += 1
                if attempts["count"] < 3:
                    raise google.api_core.exceptions.ServiceUnavailable("503 This model is currently experiencing high demand. Please try again later.")
                return DummyResponse()

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    result = gemini_service.generate_summary("Machine learning uses data to identify patterns and improve prediction accuracy.", source_type="text")

    assert attempts["count"] == 3
    assert result["summary"] == ["Third attempt succeeded."]


def test_generate_summary_retries_503_three_times_when_needed(monkeypatch):
    attempts = {"count": 0}

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                attempts["count"] += 1
                raise google.api_core.exceptions.ServiceUnavailable("503 This model is currently experiencing high demand. Please try again later.")

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    with pytest.raises(APIError) as exc:
        gemini_service.generate_summary("Example content for testing the summarization service.", source_type="text")

    assert attempts["count"] == 3
    assert exc.value.status_code == 503
    assert exc.value.message == "Gemini is temporarily unavailable due to high demand. Please try again later."


def test_model_not_found_error_returns_api_error(monkeypatch):
    attempts = {"count": 0}

    class DummyClient:
        class models:
            @staticmethod
            def generate_content(model, contents, config=None):
                attempts["count"] += 1
                raise NotFound("models/gemini-3.6-flash is not found or not supported for this API key")

    monkeypatch.setattr(gemini_service, "client", DummyClient())
    monkeypatch.setattr(gemini_service.time, "sleep", lambda seconds: None)

    with pytest.raises(APIError) as exc:
        gemini_service.generate_summary("Example content to trigger a model lookup failure.", source_type="text")

    assert attempts["count"] == 1
    assert exc.value.status_code == 502
    assert "model" in exc.value.message.lower()
