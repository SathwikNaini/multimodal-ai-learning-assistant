import os
import json
import logging
import re
from flask import jsonify

from backend.utils.exceptions import APIError

INVALID_CONTENT_MESSAGE = (
    'The provided content is too short or does not contain enough meaningful information to analyze. '
    'Please provide a document, paragraph, lecture notes, or other meaningful content.'
)


def create_error_response(message: str, status_code: int = 400):
    response = jsonify({'success': False, 'data': None, 'error': message})
    response.status_code = status_code
    return response


def create_success_response(data, status_code: int = 200):
    response = jsonify({'success': True, 'data': data, 'error': None})
    response.status_code = status_code
    return response


def validate_meaningful_content(content: str):
    if content is None:
        return False, INVALID_CONTENT_MESSAGE

    cleaned = str(content).strip()
    if not cleaned:
        return False, INVALID_CONTENT_MESSAGE

    cleaned = re.sub(r'https?://\S+|www\.\S+', ' ', cleaned)
    cleaned = cleaned.replace('\r', ' ').replace('\n', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if not cleaned:
        return False, INVALID_CONTENT_MESSAGE

    words = re.findall(r'[A-Za-z]{2,}', cleaned)
    if not words:
        return False, INVALID_CONTENT_MESSAGE

    normalized_words = [word.lower() for word in words]
    if len(normalized_words) < 3:
        return False, INVALID_CONTENT_MESSAGE

    if len(set(normalized_words)) < 2:
        return False, INVALID_CONTENT_MESSAGE

    meaningful_words = [word for word in normalized_words if len(word) >= 3]
    if len(meaningful_words) < 3:
        return False, INVALID_CONTENT_MESSAGE

    if sum(1 for word in meaningful_words if len(word) >= 5) < 2:
        return False, INVALID_CONTENT_MESSAGE

    alpha_char_count = sum(len(word) for word in meaningful_words)
    if alpha_char_count < 20:
        return False, INVALID_CONTENT_MESSAGE

    if any(word in {'hi', 'hello', 'hey', 'yo', 'hii', 'hiii'} for word in normalized_words):
        return False, INVALID_CONTENT_MESSAGE

    if not any(any(vowel in word for vowel in 'aeiou') for word in meaningful_words):
        return False, INVALID_CONTENT_MESSAGE

    return True, None


def validate_content_for_analysis(content: str) -> str:
    is_valid, error = validate_meaningful_content(content)
    if not is_valid:
        raise APIError(error, status_code=400)
    return str(content).strip()


def parse_youtube_id(url: str) -> str | None:
    if not url:
        return None

    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})',
        r'[?&]v=([A-Za-z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            if len(video_id) == 11:
                return video_id
    return None
