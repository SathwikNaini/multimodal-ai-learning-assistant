import logging
import httpx

# Monkeypatch httpx to ignore 'proxies' kwarg for legacy youtube-search-python compatibility
_orig_post = httpx.post
_orig_get = httpx.get

def _patched_post(*args, **kwargs):
    kwargs.pop('proxies', None)
    return _orig_post(*args, **kwargs)

def _patched_get(*args, **kwargs):
    kwargs.pop('proxies', None)
    return _orig_get(*args, **kwargs)

httpx.post = _patched_post
httpx.get = _patched_get

import contextlib
import requests
from requests.adapters import HTTPAdapter
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch


import time
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests
)

from backend.utils.exceptions import APIError
from backend.utils.helpers import parse_youtube_id


class _TimeoutAdapter(HTTPAdapter):
    def __init__(self, timeout=10.0, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)
    def send(self, request, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout') or self.timeout
        return super().send(request, **kwargs)


@contextlib.contextmanager
def patch_session_timeout(timeout=10.0):
    orig_init = requests.Session.__init__
    def patched_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self.mount('https://', _TimeoutAdapter(timeout=timeout))
        self.mount('http://', _TimeoutAdapter(timeout=timeout))
    requests.Session.__init__ = patched_init
    try:
        yield
    finally:
        requests.Session.__init__ = orig_init


def get_video_transcript(youtube_url: str) -> str:
    video_id = parse_youtube_id(youtube_url)
    if not video_id:
        logging.error(f"[YouTube] [Transcript] Invalid URL: {youtube_url}")
        raise APIError('Invalid YouTube URL format', status_code=400)

    logging.info(f"[YouTube] [Transcript] Extracting transcript. Video ID: {video_id}, URL: {youtube_url}")
    
    try:
        with patch_session_timeout(10.0):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Log available transcripts
        available_languages = []
        for t in transcript_list:
            available_languages.append({
                'code': t.language_code,
                'name': t.language,
                'is_generated': t.is_generated
            })
        logging.info(f"[YouTube] [Transcript] Available languages for video {video_id}: {available_languages}")
        
        transcript = None
        selected_method = ""
        
        # Priority 1: Manual English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            selected_method = "Priority 1: Manual English transcript"
        except Exception:
            pass

        # Priority 2: Manual transcript translated to English
        if not transcript:
            try:
                manuals = [t for t in transcript_list if not t.is_generated]
                translatable = [t for t in manuals if t.is_translatable]
                if translatable:
                    # Translate to English
                    transcript = translatable[0].translate('en')
                    selected_method = f"Priority 2: Manual {translatable[0].language_code} translated to English"
            except Exception:
                pass

        # Priority 3: Auto-generated English transcript
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                selected_method = "Priority 3: Auto-generated English transcript"
            except Exception:
                pass

        # Priority 4: Auto-generated transcript translated to English
        if not transcript:
            try:
                generateds = [t for t in transcript_list if t.is_generated]
                translatable = [t for t in generateds if t.is_translatable]
                if translatable:
                    transcript = translatable[0].translate('en')
                    selected_method = f"Priority 4: Auto-generated {translatable[0].language_code} translated to English"
            except Exception:
                pass

        # Priority 5: First available transcript translated to English
        if not transcript:
            try:
                first_avail = next(iter(transcript_list))
                if first_avail.is_translatable:
                    transcript = first_avail.translate('en')
                    selected_method = f"Priority 5: First available ({first_avail.language_code}) translated to English"
            except Exception:
                pass

        # Priority 6: First available transcript raw language
        if not transcript:
            try:
                transcript = next(iter(transcript_list))
                selected_method = f"Priority 6: First available ({transcript.language_code}) in raw language"
            except Exception:
                pass

        if not transcript:
            logging.error(f"[YouTube] [Transcript] No captions could be resolved for video {video_id}")
            raise APIError("No captions available", status_code=400)

        logging.info(f"[YouTube] [Transcript] Selected method: {selected_method}")
        
        # Fetch content with retries
        retries = 3
        text = None
        for attempt in range(retries):
            try:
                with patch_session_timeout(10.0):
                    text = ' '.join(item['text'] for item in transcript.fetch())
                break
            except Exception as e:
                logging.warning(f"[YouTube] [Transcript] Fetch attempt {attempt+1} failed: {str(e)}")
                if attempt == retries - 1:
                    raise e
                time.sleep(0.5)

        if not text:
            logging.error(f"[YouTube] [Transcript] Resolved transcript has empty payload for video {video_id}")
            raise APIError('No captions available', status_code=400)

        logging.info(f"[YouTube] [Transcript] Successfully retrieved transcript length: {len(text)} characters (Video: {video_id})")
        return text

    except TranscriptsDisabled as e:
        logging.warning(f"[YouTube] [Transcript] Transcripts disabled for video {video_id}. Exception: {str(e)}")
        raise APIError("Transcript disabled by creator", status_code=400)
    except NoTranscriptFound as e:
        logging.warning(f"[YouTube] [Transcript] No transcript found for video {video_id}. Exception: {str(e)}")
        raise APIError("No captions available", status_code=400)
    except VideoUnavailable as e:
        logging.warning(f"[YouTube] [Transcript] Video unavailable {video_id}. Exception: {str(e)}")
        raise APIError("Video unavailable", status_code=400)
    except TooManyRequests as e:
        logging.error(f"[YouTube] [Transcript] YouTube rate limited request {video_id}. Exception: {str(e)}")
        raise APIError("YouTube rate limited request", status_code=429)
    except APIError:
        raise
    except Exception as exc:
        exc_str = str(exc).strip()
        if "429" in exc_str or "too many requests" in exc_str.lower():
            logging.error(f"[YouTube] [Transcript] YouTube rate limited request {video_id} (inferred). Exception: {exc_str}")
            raise APIError("YouTube rate limited request", status_code=429)
        logging.error(f"[YouTube] [Transcript] Unexpected error extracting transcript for video {video_id}. Exception: {exc_str}", exc_info=True)
        raise APIError(f"Unable to retrieve YouTube transcript: {exc_str}", status_code=500)


def search_video_by_query(query: str) -> dict | None:
    try:
        results = VideosSearch(query, limit=1).result()
        video = results.get('result', [])[0] if results.get('result') else None
        if not video:
            return None

        return {
            'title': video.get('title', ''),
            'link': video.get('link', ''),
            'thumbnail': video.get('thumbnails', [{}])[0].get('url', ''),
            'channel': video.get('channel', {}).get('name', ''),
            'duration': video.get('duration', ''),
            'id': video.get('id', ''),
        }
    except Exception as exc:
        logging.error('YouTube search failed', exc_info=True)
        return None
