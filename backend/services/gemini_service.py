import logging
import json
import time
import google.generativeai as genai
import google.api_core.exceptions

from backend.config.settings import settings
from backend.utils.exceptions import APIError

# Globally tracked verified model to bypass latency of 404 fallbacks on subsequent calls
_verified_model = None

logging.info(f"[Gemini] Configuring Google Generative AI SDK (Key Configured: {settings.GEMINI_API_KEY is not None})")
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def verify_gemini_connection() -> bool:
    """Startup diagnostic verification to test Gemini API connectivity."""
    global _verified_model
    if not settings.GEMINI_API_KEY:
        logging.error("[Gemini Connection Test] GEMINI_API_KEY is missing from environment/configuration!")
        return False
        
    models_to_test = ['gemini-2.5-flash', 'gemini-2.5-flash', 'gemini-pro']
    
    logging.info("[Gemini Connection Test] Running startup connectivity check...")
    for model_name in models_to_test:
        try:
            logging.info(f"[Gemini Connection Test] Sending request to {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Respond with OK")
            logging.info(f"[Gemini Connection Test] SUCCESS! Response from {model_name}: {response.text.strip()}")
            _verified_model = model_name
            return True
        except google.api_core.exceptions.NotFound:
            logging.warning(f"[Gemini Connection Test] Model {model_name} not found (404). Trying next...")
            continue
        except google.api_core.exceptions.InvalidArgument as e:
            if "API key" in str(e) or "API_KEY" in str(e) or "key" in str(e).lower():
                logging.error(f"[Gemini Connection Test] FAILURE: Invalid API Key. Details: {str(e)}")
                return False
            logging.error(f"[Gemini Connection Test] Invalid Argument details: {str(e)}")
            continue
        except Exception as e:
            logging.error(f"[Gemini Connection Test] FAILURE with model {model_name}. Details: {str(e)}")
            return False
            
    logging.error("[Gemini Connection Test] FAILURE: All test models failed or returned NotFound.")
    return False


def parse_gemini_response(response_text: str) -> dict:
    """Parses Gemini response securely with regex extractors and raw text fallback."""
    if not response_text:
        return {'summary': ['Received empty response text.'], 'cognitive_gaps': []}
        
    cleaned = response_text.strip()
    
    # Try standard JSON parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
        
    # Regex fallback if wrapped in markdown codeblocks
    import re
    match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
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

    return {
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


def generate_summary(content: str) -> dict:
    if not settings.GEMINI_API_KEY:
        raise APIError('Gemini API key is not configured on the server. Please set GEMINI_API_KEY.', status_code=500)

    if not content or len(content.strip()) < 10:
        raise APIError('Content too short to summarize (minimum 10 characters)', status_code=400)

    is_fallback = "**FALLBACK_YOUTUBE_METADATA**" in content

    if is_fallback:
        logging.info("[Gemini] [Metadata] [Fallback] YouTube metadata fallback pattern detected. Routing specialized prompt.")
        prompt = f'''
You are a professional research analyst.
The transcript for the requested YouTube video was unavailable. However, we have retrieved the video metadata:
{content}

Please generate a high-level structured intelligence report based ONLY on this metadata (title, channel, description, views, duration).
Since the full transcript is unavailable, analyze the likely structure, context, and educational concepts from the video attributes.
Write your analysis in the style of a professional analyst report rather than a traditional summary (like ChatGPT Deep Research reports).

Output only a valid JSON object matching the following structure:
{{
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
    "📊 Views, duration, or numeric details from the metadata (e.g. view count, video length)",
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
1. "quiz" contains exactly 5 multiple choice questions.
2. "difficulty_level" must be one of "Beginner", "Intermediate", or "Advanced".
3. "knowledge_score" must be an integer between 0 and 100.
4. Output must be strictly valid JSON matching this schema, with no additional text or formatting outside the JSON block.
'''
    else:
        prompt = f'''
You are a professional research analyst.
Create a comprehensive structured intelligence report in JSON format using the provided content.
Generate the analysis in the style of a professional analyst report rather than a traditional summary (like ChatGPT Deep Research reports).

Content:
{content}

Output only a valid JSON object matching the following structure:
{{
  "main_theme": "🏆 The overarching core theme or thesis statement of the content.",
  "important_observations": [
    "🔎 Important observation / key takeaway from the content",
    "🔎 Another important observation / key takeaway"
  ],
  "major_topics": [
    "📑 Major topic or concept covered in detail",
    "📑 Another major topic"
  ],
  "key_statistics": [
    "📊 Key statistic, data point, or hard fact (include numbers/metrics)",
    "📊 Another key statistic or fact"
  ],
  "important_entities": [
    "👤 Key person, organization, company, technology, product, country, or tool and their role/impact",
    "👤 Another key entity"
  ],
  "timeline": [
    "📅 Event with date/timestamp or sequence",
    "📅 Another event"
  ],
  "turning_points": [
    "🔄 Critical turning point, decision, or shift in direction",
    "🔄 Another critical turning point"
  ],
  "strengths": [
    "⚖️ Strength: positive aspect, evidence, or advantage discussed"
  ],
  "weaknesses": [
    "⚖️ Weakness: limitation, criticism, or gap discussed"
  ],
  "core_insights": [
    "🧠 High-level analytical insight or implication of the findings",
    "🧠 Another core insight"
  ],
  "learning_gaps": [
    {{
      "concept": "Name of the missing or complex concept that needs further study",
      "reason": "Detailed explanation of why this concept is important or complex",
      "youtube_query": "A precise search query to find educational videos on YouTube about this concept"
    }}
  ],
  "quiz": [
    {{
      "question": "A multiple choice question testing understanding of the content.",
      "options": ["A) Option A text", "B) Option B text", "C) Option C text", "D) Option D text"],
      "correct_answer": "Option A text",
      "explanation": "Detailed explanation of why the correct option is right and others are wrong."
    }}
  ],
  "final_verdict": "📝 An executive summary verdict concluding the analysis and key recommendations.",
  "difficulty_level": "Intermediate",
  "knowledge_score": 85,
  "estimated_reading_time": "5 mins"
}}
Ensure that:
1. "quiz" contains exactly 5 multiple choice questions.
2. "difficulty_level" must be one of "Beginner", "Intermediate", or "Advanced".
3. "knowledge_score" must be an integer between 0 and 100.
4. Output must be strictly valid JSON matching this schema, with no additional text or formatting outside the JSON block.
'''

    global _verified_model
    models_to_try = [
        'gemini-2.5-flash',
        'gemini-2.5-flash',
        'gemini-pro'
    ]
    if _verified_model and _verified_model in models_to_try:
        # Prioritize the known working model to avoid redundant 404 retries
        models_to_try.remove(_verified_model)
        models_to_try.insert(0, _verified_model)
    
    last_error = None
    for model_name in models_to_try:
        model = genai.GenerativeModel(model_name)
        
        # Retry loop with exponential backoff
        retries = 3
        backoff = 2
        for attempt in range(retries):
            try:
                logging.info(f"[Gemini API] Dispatching request to model {model_name} (Attempt {attempt+1}/{retries})...")
                response = model.generate_content(
                    prompt,
                    generation_config={'response_mime_type': 'application/json'},
                )
                
                if not response:
                    raise APIError('Empty response object received from Gemini API', status_code=502)
                    
                # Handle safety blocks / prompt blocking
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    logging.error(f"[Gemini Safety] Prompt blocked. Reason: {response.prompt_feedback.block_reason}")
                    raise APIError(f"Summarization request was blocked by Gemini safety filters: {response.prompt_feedback.block_reason}", status_code=400)
                
                raw_text = response.text
                if not raw_text:
                    raise APIError('Gemini returned an empty text payload', status_code=502)
                    
                parsed_res = parse_gemini_response(raw_text)
                return normalize_summary_payload(parsed_res, is_fallback=is_fallback)
                
            except google.api_core.exceptions.NotFound as exc:
                logging.warning(f"[Gemini API] Model {model_name} not found. Skipping to next model.")
                last_error = exc
                break # break retry loop, try next model name
            except google.api_core.exceptions.ResourceExhausted as exc:
                logging.warning(f"[Gemini API] Quota Limit Exceeded. Backing off for {backoff}s...")
                last_error = exc
                time.sleep(backoff)
                backoff *= 2
            except google.api_core.exceptions.InvalidArgument as exc:
                if "API key" in str(exc) or "API_KEY" in str(exc) or "key" in str(exc).lower():
                    logging.error("[Gemini API] Invalid API key error detected.")
                    raise APIError("Invalid Gemini API Key provided. Please check configuration settings.", status_code=401)
                raise APIError(f"Invalid request argument: {str(exc)}", status_code=400)
            except Exception as exc:
                logging.error(f"[Gemini API] Temporary error: {str(exc)}")
                last_error = exc
                time.sleep(1)
                
    # If all models failed
    logging.error(f"[Gemini API] All models failed. Last error: {str(last_error)}")
    error_message = str(last_error) if last_error else "Unknown API failure"
    
    if "404" in error_message or "not found" in error_message.lower():
        raise APIError("Target Gemini models (including gemini-2.5-flash) are unavailable or not supported for this API key.", status_code=502)
    elif "quota" in error_message.lower() or "exhausted" in error_message.lower():
        raise APIError("Gemini API quota exceeded. Please wait a few minutes before trying again.", status_code=429)
        
    raise APIError(f"Failed to generate summary with Gemini: {error_message}", status_code=502)
