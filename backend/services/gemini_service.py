import logging
import json
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import google.api_core.exceptions

from backend.config.settings import settings
from backend.utils.exceptions import APIError
from backend.utils.helpers import validate_content_for_analysis

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

# Globally tracked verified model to bypass latency of 404 fallbacks on subsequent calls
_verified_model = None
DAILY_QUOTA_EXCEEDED_MESSAGE = (
    "Gemini daily API quota exceeded for this project. Please wait for the quota to reset or upgrade the Gemini API plan."
)
TEMPORARY_UNAVAILABLE_MESSAGE = (
    "Gemini is temporarily unavailable due to high demand. Please try again later."
)

client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
logging.info("[Gemini API] Configured model: %s", settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL)


def resolve_gemini_model_name() -> str:
    configured_model = (settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    model_name = configured_model.lower()
    if model_name in {'gemini-pro', 'gemini-2.5-flash'}:
        logging.warning("[Gemini] Legacy model '%s' is not supported. Replacing it with '%s'.", configured_model, DEFAULT_GEMINI_MODEL)
        return DEFAULT_GEMINI_MODEL
    return configured_model


def is_daily_quota_exhaustion_error(exc: Exception) -> bool:
    if exc is None:
        return False

    message = str(exc).lower()
    if "you exceeded your current quota" in message:
        return True
    if "generate_content_free_tier_requests" in message:
        return True
    if "generaterequestsperdayperm" in message or "generate requests per day per model" in message:
        return True
    if "quota" in message and ("429" in message or "resource_exhausted" in message or "free tier" in message):
        return True
    if "resource_exhausted" in message and "quota" in message:
        return True
    return False


def _get_error_status_code(exc: Exception):
    if exc is None:
        return None
    code = getattr(exc, 'code', None)
    if code is not None:
        try:
            return int(code)
        except (TypeError, ValueError):
            pass
    status_code = getattr(exc, 'status_code', None)
    if status_code is not None:
        try:
            return int(status_code)
        except (TypeError, ValueError):
            pass
    message = str(exc).lower()
    if '503' in message:
        return 503
    if '429' in message:
        return 429
    if '404' in message:
        return 404
    return None


def is_transient_503_error(exc: Exception) -> bool:
    if exc is None:
        return False
    if _get_error_status_code(exc) == 503:
        return True
    message = str(exc).lower()
    return '503' in message and ('unavailable' in message or 'temporarily unavailable' in message or 'high demand' in message)


def is_model_not_found_error(exc: Exception) -> bool:
    if exc is None:
        return False
    if _get_error_status_code(exc) == 404:
        return True
    message = str(exc).lower()
    return 'not found' in message and 'model' in message


def classify_gemini_error(exc: Exception):
    message = str(exc).lower()
    if is_daily_quota_exhaustion_error(exc):
        return 429, DAILY_QUOTA_EXCEEDED_MESSAGE
    if is_transient_503_error(exc):
        return 503, TEMPORARY_UNAVAILABLE_MESSAGE
    if "quota" in message or "resource_exhausted" in message or "rate limit" in message:
        return 429, "Gemini API quota exceeded. Please wait a few minutes and try again, or upgrade your API plan."
    if is_model_not_found_error(exc) or "not found" in message or "404" in message or "no longer available" in message:
        return 502, "Target Gemini model is unavailable or not supported for this API key. Please update GEMINI_MODEL to a supported model."
    if "api key" in message or "invalid api key" in message or "api_key" in message:
        return 401, "Invalid Gemini API Key provided. Please check configuration settings."
    if "safety" in message or "blocked" in message:
        return 400, "Summarization request was blocked by Gemini safety filters. Please provide more clear, valid content."
    return 502, TEMPORARY_UNAVAILABLE_MESSAGE if is_transient_503_error(exc) else f"Failed to generate summary with Gemini: {exc}"


def verify_gemini_connection() -> bool:
    """Startup diagnostic verification to test Gemini API connectivity."""
    global _verified_model
    if not settings.GEMINI_API_KEY:
        logging.error("[Gemini Connection Test] GEMINI_API_KEY is missing from environment/configuration!")
        return False

    model_name = resolve_gemini_model_name()
    logging.info("[Gemini Connection Test] Running startup connectivity check on configured model: %s", model_name)
    try:
        if client is None:
            raise RuntimeError("Gemini client is not configured.")
        logging.info(f"[Gemini Connection Test] Sending request to {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Respond with OK",
            config=types.GenerateContentConfig(response_mime_type="text/plain"),
        )
        response_text = getattr(response, "text", "") or ""
        logging.info(f"[Gemini Connection Test] SUCCESS! Response from {model_name}: {response_text.strip()}")
        _verified_model = model_name
        return True
    except Exception as e:
        status_code, user_message = classify_gemini_error(e)
        logging.error(f"[Gemini Connection Test] FAILURE with model {model_name}. Status {status_code}. {user_message}")
        return False


def _coerce_string_list(value, key_hint: str = 'value'):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    elif isinstance(value, dict):
        for candidate_key in ('points', 'items', 'summary', 'content', 'key_points', 'main_points', 'details', 'value'):
            if candidate_key in value:
                return _coerce_string_list(value[candidate_key], candidate_key)
        return [json.dumps(value, ensure_ascii=False)]
    else:
        text = str(value).strip()
        return [text] if text else []

    normalized = []
    for item in items:
        if isinstance(item, dict):
            nested = _coerce_string_list(item)
            normalized.extend(nested)
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _extract_summary_list(payload, seen=None):
    if not isinstance(payload, dict):
        return []
    if seen is None:
        seen = set()
    if id(payload) in seen:
        return []
    seen.add(id(payload))

    summary_variants = [
        'summary',
        'module_summary',
        'comprehensive_summary',
        'comprehensive_module_summary',
        'key_points',
        'main_points',
        'overview',
        'summary_points',
    ]

    for key in summary_variants:
        if key in payload:
            value = payload.get(key)
            extracted = _coerce_string_list(value, key)
            if extracted:
                return extracted

    for nested_key in ('analysis', 'result', 'data', 'report', 'output', 'response', 'content'):
        if nested_key in payload and isinstance(payload[nested_key], (dict, list)):
            nested = _extract_summary_list(payload[nested_key], seen)
            if nested:
                return nested

    for value in payload.values():
        if isinstance(value, dict):
            nested = _extract_summary_list(value, seen)
            if nested:
                return nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = _extract_summary_list(item, seen)
                    if nested:
                        return nested

    return []


def parse_gemini_response(response_text: str) -> dict:
    """Parses Gemini response securely with regex extractors and raw text fallback."""
    if not response_text:
        return {'summary': ['Received empty response text.'], 'cognitive_gaps': []}

    cleaned = response_text.strip()

    # Handle markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.DOTALL)

    # Try standard JSON parsing
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            logging.info("[Gemini Response Parser] Parsed Gemini response keys: %s", sorted(parsed.keys()))
            print("========== GEMINI DEBUG ==========")
            print("Parsed response type:", type(parsed).__name__)
            print("Parsed response keys:", list(parsed.keys()))
            print("Raw summary:", parsed.get("summary"))
            print("Raw module_summary:", parsed.get("module_summary"))
            print("Raw comprehensive_summary:", parsed.get("comprehensive_summary"))
            print("Raw comprehensive_module_summary:", parsed.get("comprehensive_module_summary"))
            print("Raw key_points:", parsed.get("key_points"))
            print("Raw main_points:", parsed.get("main_points"))
            print("Raw overview:", parsed.get("overview"))
            print("Raw summary_points:", parsed.get("summary_points"))
            print("Main theme:", parsed.get("main_theme"))
            print("Major topics:", parsed.get("major_topics"))
            print("Core insights:", parsed.get("core_insights"))
            print("=================================")
            return parsed
    except json.JSONDecodeError:
        pass

    # Regex fallback if wrapped in markdown codeblocks
    import re
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                logging.info("[Gemini Response Parser] Parsed fenced Gemini response keys: %s", sorted(parsed.keys()))
                return parsed
        except json.JSONDecodeError:
            pass

    # Return raw text wrap
    logging.warning("[Gemini Response Parser] Fallback triggered. Returning raw text wrapped in structured JSON format.")
    return {
        'summary': [cleaned],
        'cognitive_gaps': [],
        'is_raw': True
    }


def normalize_summary_payload(payload: dict, is_fallback: bool = False) -> dict:
    """Ensures that the summary payload conforms strictly to the expected structure and types."""
    if not isinstance(payload, dict):
        payload = {}

    summary = _extract_summary_list(payload)

    if not summary and 'important_observations' in payload:
        summary = _coerce_string_list(payload.get('important_observations'), 'important_observations')

    summary = [str(item).strip() for item in summary if str(item).strip()]

    # 1. Main Theme
    main_theme = str(payload.get('main_theme', '')).strip()
    if not main_theme:
        main_theme = "Not specified."

    # 2. Important Observations
    obs = payload.get('important_observations')
    if obs is None:
        obs = payload.get('summary', [])
    if isinstance(obs, str):
        obs = [obs]
    elif not isinstance(obs, list):
        obs = []
    normalized_obs = [str(item).strip() for item in obs if item]
    if not normalized_obs:
        normalized_obs = ["No key observations generated."]
    
    if is_fallback:
        warning_msg = "⚠ Full transcript unavailable. Analysis generated from video metadata only."
        normalized_obs = [x for x in normalized_obs if "Full transcript unavailable" not in x]
        normalized_obs.append(warning_msg)

    # 3. Major Topics
    major_topics = payload.get('major_topics', [])
    if isinstance(major_topics, str):
        major_topics = [major_topics]
    elif not isinstance(major_topics, list):
        major_topics = []
    normalized_topics = [str(item).strip() for item in major_topics if item]

    # 4. Key Statistics
    key_statistics = payload.get('key_statistics', [])
    if isinstance(key_statistics, str):
        key_statistics = [key_statistics]
    elif not isinstance(key_statistics, list):
        key_statistics = []
    normalized_stats = [str(item).strip() for item in key_statistics if item]

    # 5. Important Entities
    entities = payload.get('important_entities')
    if entities is None:
        entities = payload.get('important_people', [])
    if isinstance(entities, str):
        entities = [entities]
    elif not isinstance(entities, list):
        entities = []
    normalized_entities = [str(item).strip() for item in entities if item]

    # 6. Timeline
    timeline = payload.get('timeline', [])
    if isinstance(timeline, str):
        timeline = [timeline]
    elif not isinstance(timeline, list):
        timeline = []
    normalized_timeline = [str(item).strip() for item in timeline if item]

    # 7. Turning Points
    turning_points = payload.get('turning_points', [])
    if isinstance(turning_points, str):
        turning_points = [turning_points]
    elif not isinstance(turning_points, list):
        turning_points = []
    normalized_turning = [str(item).strip() for item in turning_points if item]

    # 8. Strengths
    strengths = payload.get('strengths', [])
    if isinstance(strengths, str):
        strengths = [strengths]
    elif not isinstance(strengths, list):
        strengths = []
    normalized_strengths = [str(item).strip() for item in strengths if item]

    # 9. Weaknesses
    weaknesses = payload.get('weaknesses', [])
    if isinstance(weaknesses, str):
        weaknesses = [weaknesses]
    elif not isinstance(weaknesses, list):
        weaknesses = []
    normalized_weaknesses = [str(item).strip() for item in weaknesses if item]

    # Fallback/merge if strengths_weaknesses is returned
    sw = payload.get('strengths_weaknesses', [])
    if not normalized_strengths and not normalized_weaknesses and sw:
        if isinstance(sw, list):
            for item in sw:
                item_str = str(item).strip()
                if 'strength' in item_str.lower():
                    normalized_strengths.append(item_str)
                elif 'weakness' in item_str.lower():
                    normalized_weaknesses.append(item_str)
                else:
                    normalized_strengths.append(item_str)

    # 10. Core Insights
    core_insights = payload.get('core_insights', [])
    if isinstance(core_insights, str):
        core_insights = [core_insights]
    elif not isinstance(core_insights, list):
        core_insights = []
    normalized_insights = [str(item).strip() for item in core_insights if item]

    # 11. Learning Gaps
    gaps = payload.get('learning_gaps')
    if gaps is None:
        gaps = payload.get('cognitive_gaps', [])
    if not isinstance(gaps, list):
        gaps = []
        
    normalized_gaps = []
    for gap in gaps:
        if isinstance(gap, dict):
            concept = str(gap.get('concept', '')).strip()
            reason = str(gap.get('reason', '')).strip()
            youtube_query = str(gap.get('youtube_query', '')).strip()
            
            if not concept:
                concept = "Key Concept"
            if not youtube_query:
                youtube_query = concept
                
            normalized_gaps.append({
                'concept': concept,
                'reason': reason or f"Recommended learning resource for: {concept}",
                'youtube_query': youtube_query
            })
        elif isinstance(gap, str):
            concept = gap.strip()
            if concept:
                normalized_gaps.append({
                    'concept': concept,
                    'reason': f"Recommended learning resource for: {concept}",
                    'youtube_query': concept
                })

    # 12. Quiz Questions
    quiz = payload.get('quiz', [])
    if not isinstance(quiz, list):
        quiz = []
    normalized_quiz = []
    for q in quiz:
        if isinstance(q, dict):
            question = str(q.get('question', '')).strip()
            options = q.get('options', [])
            correct_answer = str(q.get('correct_answer', '')).strip()
            explanation = str(q.get('explanation', '')).strip()
            if not isinstance(options, list):
                options = []
            options = [str(opt).strip() for opt in options if opt]
            if question:
                normalized_quiz.append({
                    'question': question,
                    'options': options,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })

    # 13. Final Verdict
    final_verdict = str(payload.get('final_verdict', '')).strip()
    if not final_verdict:
        final_verdict = "Not specified."

    # 14. Difficulty Level
    diff = str(payload.get('difficulty_level', 'Intermediate')).strip()
    if diff not in ["Beginner", "Intermediate", "Advanced"]:
        diff = "Intermediate"

    # 15. Knowledge Score
    try:
        score = int(payload.get('knowledge_score', 75))
        if not (0 <= score <= 100):
            score = 75
    except Exception:
        score = 75

    # 16. Estimated Reading Time (based on observations summary length)
    total_words = sum(len(point.split()) for point in normalized_obs)
    # Average reading speed is 200 words per minute
    mins = max(1, round(total_words / 200))
    estimated_reading_time = f"{mins} min" if mins == 1 else f"{mins} mins"

    normalized_payload = {
        'summary': summary,
        'main_theme': main_theme,
        'important_observations': normalized_obs,
        'major_topics': normalized_topics,
        'key_statistics': normalized_stats,
        'important_entities': normalized_entities,
        'timeline': normalized_timeline,
        'turning_points': normalized_turning,
        'strengths': normalized_strengths,
        'weaknesses': normalized_weaknesses,
        'core_insights': normalized_insights,
        'learning_gaps': normalized_gaps,
        'quiz': normalized_quiz,
        'final_verdict': final_verdict,
        'difficulty_level': diff,
        'knowledge_score': score,
        'estimated_reading_time': estimated_reading_time
    }
    logging.info("[Gemini Normalization] Normalized response keys: %s", sorted(normalized_payload.keys()))
    return normalized_payload


def generate_summary(content: str, source_type: str = 'text') -> dict:
    if not settings.GEMINI_API_KEY:
        raise APIError('Gemini API key is not configured on the server. Please set GEMINI_API_KEY.', status_code=500)

    content = validate_content_for_analysis(content)
    is_fallback = source_type == 'youtube_metadata' or "SOURCE TYPE:\nYouTube metadata fallback" in content or "**FALLBACK_YOUTUBE_METADATA**" in content

    if is_fallback:
        logging.info("[Gemini] [Metadata] [Fallback] YouTube metadata fallback pattern detected. Routing specialized prompt.")
        prompt = f'''
You are analyzing a YouTube video using metadata because the transcript was unavailable or insufficient.

SOURCE TYPE:
YouTube metadata fallback

Use ONLY the following metadata to infer the likely topic, context, and theme of the video. Do not pretend this is a complete transcript.

Metadata:
{content}

Summarize the content based on what is actually available in the metadata. If the transcript is unavailable, clearly state that the summary is based on metadata rather than the full spoken content.

Return JSON only with the required schema. The `summary` field is REQUIRED and must contain 5-10 concise points directly supported by the available metadata.

{{
  "summary": [
    "Actual point supported by the metadata",
    "Another point supported by the metadata"
  ],
  "main_theme": "🏆 Overarching theme of this video based on the title/description",
  "important_observations": [
    "🔎 Important observation / key detail extracted from the metadata description",
    "🔎 Another important observation from the metadata description"
  ],
  "major_topics": [
    "📑 Likely major topic covered by this video",
    "📑 Another likely major topic"
  ],
  "key_statistics": [
    "📊 Views, duration, or numeric details from the metadata",
    "📊 Another key statistic from description"
  ],
  "important_entities": [
    "👤 Channel name, creator, companies, tools, products, countries, or organizations mentioned in the metadata",
    "👤 Another key entity mentioned"
  ],
  "timeline": [
    "📅 Published date or chronological cues from description"
  ],
  "turning_points": [
    "🔄 Likely key educational milestones or target outcomes for the video"
  ],
  "strengths": [
    "⚖️ Strength: likely focus area or creator expertise"
  ],
  "weaknesses": [
    "⚖️ Weakness: analysis generated from metadata only, full transcript unavailable"
  ],
  "core_insights": [
    "🧠 Core takeaway regarding the video's expected value or content focus",
    "🧠 Another core insight"
  ],
  "learning_gaps": [
    {{
      "concept": "Suggested research topic diving deeper into the subject",
      "reason": "Detailed study gap explanation.",
      "youtube_query": "Suggested search query"
    }}
  ],
  "quiz": [
    {{
      "question": "A multiple choice question testing likely concepts from the video topic.",
      "options": ["A) Option A text", "B) Option B text", "C) Option C text", "D) Option D text"],
      "correct_answer": "Option A text",
      "explanation": "Detailed explanation of why the correct option is right."
    }}
  ],
  "final_verdict": "📝 Executive summary verdict concluding the metadata-based analysis. Note that the full transcript was unavailable.",
  "difficulty_level": "Beginner",
  "knowledge_score": 50,
  "estimated_reading_time": "3 mins"
}}

Ensure that:
1. The `summary` field contains 5-10 concise points.
2. `quiz` contains exactly 5 multiple choice questions.
3. `difficulty_level` must be one of "Beginner", "Intermediate", or "Advanced".
4. `knowledge_score` must be an integer between 0 and 100.
5. Output must be strictly valid JSON with no extra text outside the JSON object.
'''
    else:
        prompt = f'''
You are analyzing a YouTube video transcript.

Summarize ONLY the information contained in the transcript.
Do not invent facts.
Do not analyze the URL.
Do not produce generic advice.
Do not say the content is meaningless when a valid transcript is provided.

SOURCE TYPE:
YouTube transcript

Transcript content:
{content}

Generate a structured analysis.
The `summary` field is REQUIRED and must contain 5-10 concise points directly supported by the transcript.

Return JSON only:
{{
  "summary": [
    "...",
    "...",
    "..."
  ],
  "important_observations": [],
  "major_topics": [],
  "key_statistics": [],
  "important_entities": [],
  "timeline": [],
  "turning_points": [],
  "strengths": [],
  "weaknesses": [],
  "core_insights": [],
  "learning_gaps": [],
  "quiz": [],
  "main_theme": "",
  "final_verdict": "",
  "difficulty_level": "",
  "estimated_reading_time": "",
  "knowledge_score": 0
}}

Requirements:
- `summary` must include 5-10 actual points supported by the transcript.
- Do not return an empty array for `summary`.
- Do not include the URL or video ID as the summary.
- Output must be valid JSON only.
'''

    global _verified_model
    model_name = resolve_gemini_model_name()
    _verified_model = model_name
    logging.info("[Gemini API] Actual analysis model: %s", model_name)

    retries = 3
    backoff = 2
    last_error = None
    for attempt in range(retries):
        try:
            logging.info(f"[Gemini API] Dispatching request to model {model_name} (Attempt {attempt+1}/{retries})...")
            if client is None:
                raise RuntimeError('Gemini client is not configured.')

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json'),
            )

            if not response:
                raise APIError('Empty response object received from Gemini API', status_code=502)

            prompt_feedback = getattr(response, 'prompt_feedback', None)
            if prompt_feedback and getattr(prompt_feedback, 'block_reason', None):
                logging.error(f"[Gemini Safety] Prompt blocked. Reason: {prompt_feedback.block_reason}")
                raise APIError(f"Summarization request was blocked by Gemini safety filters: {prompt_feedback.block_reason}", status_code=400)

            raw_text = getattr(response, 'text', None) or ""
            if not raw_text:
                raise APIError('Gemini returned an empty text payload', status_code=502)

            parsed_res = parse_gemini_response(raw_text)
            logging.info("[Gemini] Parsed response keys: %s", sorted(parsed_res.keys()) if isinstance(parsed_res, dict) else type(parsed_res).__name__)
            normalized_res = normalize_summary_payload(parsed_res, is_fallback=is_fallback)
            logging.info("[Gemini API] Returning normalized response keys: %s", sorted(normalized_res.keys()))
            return normalized_res

        except google.api_core.exceptions.NotFound as exc:
            logging.warning(f"[Gemini API] Model {model_name} not found. This likely means the configured model is unsupported.")
            last_error = exc
            break
        except genai_errors.ClientError as exc:
            if getattr(exc, 'code', None) == 404 or is_model_not_found_error(exc):
                logging.warning(f"[Gemini API] Model {model_name} not found. This likely means the configured model is unsupported.")
                last_error = exc
                break
            if getattr(exc, 'code', None) == 429 or is_daily_quota_exhaustion_error(exc):
                logging.warning("[Gemini API] Daily quota exhausted. Stopping retries immediately.")
                raise APIError(DAILY_QUOTA_EXCEEDED_MESSAGE, status_code=429)
            if getattr(exc, 'code', None) == 503 or is_transient_503_error(exc):
                logging.warning("[Gemini API] Temporary 503 UNAVAILABLE.")
                if attempt < retries - 1:
                    delay = backoff
                    logging.warning("[Gemini API] Retrying in %s seconds... (Attempt %s/%s)", delay, attempt + 2, retries)
                    last_error = exc
                    time.sleep(delay)
                    backoff *= 2
                    continue
                last_error = exc
                break
            last_error = exc
            raise APIError(str(exc), status_code=getattr(exc, 'code', 502) or 502)
        except google.api_core.exceptions.TooManyRequests as exc:
            if is_daily_quota_exhaustion_error(exc):
                logging.warning("[Gemini API] Daily quota exhausted. Stopping retries immediately.")
                raise APIError(DAILY_QUOTA_EXCEEDED_MESSAGE, status_code=429)
            logging.warning(f"[Gemini API] Too Many Requests. Backing off for {backoff}s...")
            last_error = exc
            time.sleep(backoff)
            backoff *= 2
        except google.api_core.exceptions.ResourceExhausted as exc:
            if is_daily_quota_exhaustion_error(exc):
                logging.warning("[Gemini API] Daily quota exhausted. Stopping retries immediately.")
                raise APIError(DAILY_QUOTA_EXCEEDED_MESSAGE, status_code=429)
            logging.warning(f"[Gemini API] Quota Limit Exceeded. Backing off for {backoff}s...")
            last_error = exc
            time.sleep(backoff)
            backoff *= 2
        except google.api_core.exceptions.InvalidArgument as exc:
            if "API key" in str(exc) or "API_KEY" in str(exc) or "key" in str(exc).lower():
                logging.error("[Gemini API] Invalid API key error detected.")
                raise APIError("Invalid Gemini API Key provided. Please check configuration settings.", status_code=401)
            raise APIError(f"Invalid request argument: {str(exc)}", status_code=400)
        except genai_errors.ServerError as exc:
            if getattr(exc, 'code', None) == 503 or is_transient_503_error(exc):
                logging.warning("[Gemini API] Temporary 503 UNAVAILABLE.")
                if attempt < retries - 1:
                    delay = backoff
                    logging.warning("[Gemini API] Retrying in %s seconds... (Attempt %s/%s)", delay, attempt + 2, retries)
                    last_error = exc
                    time.sleep(delay)
                    backoff *= 2
                    continue
                last_error = exc
                break
            last_error = exc
            raise APIError(TEMPORARY_UNAVAILABLE_MESSAGE if is_transient_503_error(exc) else str(exc), status_code=getattr(exc, 'code', 502) or 502)
        except Exception as exc:
            if is_daily_quota_exhaustion_error(exc):
                logging.warning("[Gemini API] Daily quota exhausted. Stopping retries immediately.")
                raise APIError(DAILY_QUOTA_EXCEEDED_MESSAGE, status_code=429)
            if is_model_not_found_error(exc):
                logging.warning(f"[Gemini API] Model {model_name} not found. This likely means the configured model is unsupported.")
                last_error = exc
                break
            if is_transient_503_error(exc):
                logging.warning("[Gemini API] Temporary 503 UNAVAILABLE.")
                if attempt < retries - 1:
                    delay = backoff
                    logging.warning("[Gemini API] Retrying in %s seconds... (Attempt %s/%s)", delay, attempt + 2, retries)
                    last_error = exc
                    time.sleep(delay)
                    backoff *= 2
                    continue
                last_error = exc
                break
            logging.error(f"[Gemini API] Temporary error: {str(exc)}")
            last_error = exc
            time.sleep(1)

    logging.error(f"[Gemini API] Final model attempt failed. Last error: {str(last_error)}")
    status_code, user_message = classify_gemini_error(last_error or Exception('Unknown API failure'))
    raise APIError(user_message, status_code=status_code)
