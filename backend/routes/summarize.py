import logging
import json
from flask import Blueprint, request, jsonify
from PIL import Image
from youtube_transcript_api import YouTubeTranscriptApi

from backend.services.file_service import extract_text_from_file
from backend.services.youtube_service import get_video_transcript, search_video_by_query
from backend.services.gemini_service import generate_summary
from backend.utils.exceptions import APIError
from backend.utils.helpers import create_success_response, create_error_response, parse_youtube_id
from backend.config.settings import settings

summarize_router = Blueprint('summarize', __name__)


@summarize_router.route('/api/summarize', methods=['POST'])
def summarize_content():
    logging.info("[Route] POST /api/summarize request received.")
    
    # Check API key configuration status
    if not settings.GEMINI_API_KEY:
        logging.error("[Route] Request failed: GEMINI_API_KEY is not configured.")
        return create_error_response('Gemini API key not configured on the server', status_code=500)

    text_input = request.form.get('text', '').strip()
    youtube_url = request.form.get('youtube_url', '').strip()
    file = request.files.get('file')

    # Log incoming request characteristics
    logging.info(f"[Route] Params - Text Input length: {len(text_input)}, YouTube URL: '{youtube_url}', Has File: {file is not None}")
    if file:
        logging.info(f"[Route] File Details - Filename: '{file.filename}', ContentType: '{file.content_type}'")

    if not any([text_input, youtube_url, file]):
        logging.warning("[Route] Request validation failed: No input provided.")
        return create_error_response('Please provide text, file, or YouTube URL.', status_code=400)

    try:
        if text_input:
            logging.info("[Route] Processing mode: Raw Text Input")
            input_content = text_input
        elif youtube_url:
            logging.info(f"[Route] Processing mode: YouTube Transcript Extraction ({youtube_url})")
            try:
                input_content = get_video_transcript(youtube_url)
                logging.info(f"[Route] Successfully fetched YouTube transcript ({len(input_content)} chars)")
            except Exception as yt_exc:
                logging.warning(f"[Route] [Transcript] Transcript extraction failed ({str(yt_exc)}). Attempting metadata fallback...")
                
                title = "Unknown Title"
                channel = "Unknown Channel"
                description = "No description available"
                views = "Unknown views"
                duration = "Unknown duration"
                published_date = "Unknown publish date"
                
                video_id = parse_youtube_id(youtube_url)
                fetched_meta = False
                
                if video_id:
                    # 1. Try youtubesearchpython Video.getInfo
                    try:
                        from youtubesearchpython import Video
                        standard_url = f"https://www.youtube.com/watch?v={video_id}"
                        logging.info(f"[Route] [Fallback] Querying youtubesearchpython for video_id {video_id}")
                        info = Video.getInfo(standard_url)
                        title = info.get("title") or title
                        channel = info.get("channel", {}).get("name") or channel
                        description = info.get("description") or description
                        views = info.get("viewCount", {}).get("text") or views
                        published_date = info.get("publishDate") or published_date
                        
                        duration_seconds = info.get("duration", {}).get("secondsText", "0")
                        try:
                            seconds = int(duration_seconds)
                            if seconds >= 3600:
                                duration = f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
                            else:
                                duration = f"{seconds // 60}:{seconds % 60:02d}"
                        except Exception:
                            duration = "Unknown duration"
                        
                        fetched_meta = True
                        logging.info(f"[Route] [Fallback] Successfully retrieved video metadata using youtubesearchpython. Title: {title}")
                    except Exception as meta_exc:
                        logging.warning(f"[Route] [Fallback] youtubesearchpython failed: {str(meta_exc)}. Trying oEmbed fallback...")

                    # 2. Try oEmbed API if youtubesearchpython failed
                    if not fetched_meta:
                        try:
                            import httpx
                            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                            logging.info(f"[Route] [Fallback] Querying oEmbed for video_id {video_id}")
                            res = httpx.get(oembed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
                            if res.status_code == 200:
                                oembed_data = res.json()
                                title = oembed_data.get("title") or title
                                channel = oembed_data.get("author_name") or channel
                                description = "No description available (fetched via oEmbed)"
                                fetched_meta = True
                                logging.info(f"[Route] [Fallback] Successfully retrieved video metadata via oEmbed. Title: {title}")
                        except Exception as oembed_exc:
                            logging.warning(f"[Route] [Fallback] oEmbed failed: {str(oembed_exc)}")

                # 3. Final fallback: standard placeholder if all failed
                if not fetched_meta:
                    logging.info(f"[Route] [Fallback] Using default placeholder metadata for video_id {video_id or 'unknown'}")
                    description = "Detailed transcripts and video metadata could not be fetched due to YouTube rate limits, restrictions, or private settings."
                
                input_content = (
                    f"**FALLBACK_YOUTUBE_METADATA**\n\n"
                    f"Title: {title}\n"
                    f"Channel: {channel}\n"
                    f"Description: {description}\n"
                    f"Views: {views}\n"
                    f"Duration: {duration}\n"
                    f"Published Date: {published_date}"
                )
        else:
            logging.info("[Route] Processing mode: File Extraction")
            extracted = extract_text_from_file(file)
            if isinstance(extracted, Image.Image):
                logging.warning("[Route] Extracted result is a PIL Image object (unsupported in standard text route).")
                raise APIError('Image summarization is not supported in this API version', status_code=400)
            input_content = extracted
            logging.info(f"[Route] Successfully extracted document content ({len(input_content)} chars)")

        logging.info("[Route] Invoking Gemini summarization service...")
        summary_payload = generate_summary(input_content)

        logging.info("[Route] Validating Gemini summary payload schema...")
        if not isinstance(summary_payload, dict):
            logging.error(f"[Route] Invalid payload type: {type(summary_payload)}. Payload: {summary_payload}")
            raise APIError('AI response format is invalid (not a JSON object)', status_code=502)

        learning_gaps = summary_payload.get('learning_gaps', [])
        logging.info(f"[Route] Processing {len(learning_gaps) if isinstance(learning_gaps, list) else 0} learning gaps...")
        if isinstance(learning_gaps, list):
            for i, gap in enumerate(learning_gaps):
                # Ensure each gap item is a dictionary to prevent AttributeErrors
                if not isinstance(gap, dict):
                    logging.warning(f"[Route] Gap item at index {i} is not a dict: {gap}. Normalizing.")
                    gap = {
                        'concept': str(gap),
                        'reason': f"Recommended learning resource for: {gap}",
                        'youtube_query': str(gap)
                    }
                    learning_gaps[i] = gap

                query = gap.get('youtube_query')
                if query:
                    logging.info(f"[Route] Searching YouTube matching video for query {i+1}: '{query}'")
                    try:
                        gap['video'] = search_video_by_query(query)
                    except Exception as yt_err:
                        logging.error(f"[Route] YouTube search failed for query '{query}': {str(yt_err)}")
                        gap['video'] = None

        logging.info("[Route] Request completed successfully.")
        return create_success_response(summary_payload)

    except APIError as exc:
        logging.warning(f"[Route] API error caught: {exc.message} (status: {exc.status_code})")
        return exc.to_response()
    except Exception as exc:
        logging.exception("[Route] Unhandled server error in summarize endpoint")
        # Expose exception name in development environment
        error_msg = f"Internal server error: {str(exc)}" if settings.FLASK_DEBUG or settings.FLASK_ENV == 'development' else "Internal server error"
        return create_error_response(error_msg, status_code=500)


@summarize_router.route('/api/debug/youtube/<video_id>', methods=['GET'])
def debug_youtube_transcript(video_id):
    logging.info(f"[YouTube] [Transcript] [Debug] GET /api/debug/youtube/{video_id} received.")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        available_languages = []
        manual_captions = False
        auto_captions = False
        
        for t in transcript_list:
            available_languages.append(t.language_code)
            if t.is_generated:
                auto_captions = True
            else:
                manual_captions = True
                
        # Resolve the selected transcript using the same hierarchy as get_video_transcript
        transcript = None
        # Priority 1: Manual English
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except Exception:
            pass
        # Priority 2: Manual translated
        if not transcript:
            try:
                manuals = [t for t in transcript_list if not t.is_generated]
                translatable = [t for t in manuals if t.is_translatable]
                if translatable:
                    transcript = translatable[0].translate('en')
            except Exception:
                pass
        # Priority 3: Auto English
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except Exception:
                pass
        # Priority 4: Auto translated
        if not transcript:
            try:
                generateds = [t for t in transcript_list if t.is_generated]
                translatable = [t for t in generateds if t.is_translatable]
                if translatable:
                    transcript = translatable[0].translate('en')
            except Exception:
                pass
        # Priority 5: First available translated
        if not transcript:
            try:
                first_avail = next(iter(transcript_list))
                if first_avail.is_translatable:
                    transcript = first_avail.translate('en')
            except Exception:
                pass
        # Priority 6: First available raw
        if not transcript:
            try:
                transcript = next(iter(transcript_list))
            except Exception:
                pass

        selected_language = "None"
        transcript_length = 0
        if transcript:
            selected_language = transcript.language_code
            text = ' '.join(item['text'] for item in transcript.fetch())
            transcript_length = len(text)
            
        return jsonify({
            "video_id": video_id,
            "available_languages": available_languages,
            "manual_captions": manual_captions,
            "auto_captions": auto_captions,
            "selected_language": selected_language,
            "transcript_length": transcript_length,
            "status": "success"
        })
        
    except Exception as exc:
        logging.warning(f"[YouTube] [Transcript] [Debug] Failed for {video_id}. Error: {str(exc)}")
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, TooManyRequests
        
        exc_str = str(exc).strip()
        
        if isinstance(exc, TranscriptsDisabled):
            error_msg = "Transcript disabled"
        elif isinstance(exc, NoTranscriptFound):
            error_msg = "No captions available"
        elif isinstance(exc, VideoUnavailable):
            error_msg = "Video unavailable"
        elif isinstance(exc, TooManyRequests) or "429" in exc_str or "too many requests" in exc_str.lower():
            error_msg = "YouTube rate limited request"
        else:
            error_msg = exc_str.split('\n')[0] if exc_str else "Unknown error"
            
        return jsonify({
            "status": "failed",
            "error": error_msg
        }), 400

