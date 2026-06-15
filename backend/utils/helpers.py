import os
import json
import logging
import re
from flask import jsonify


def create_error_response(message: str, status_code: int = 400):
    response = jsonify({'success': False, 'data': None, 'error': message})
    response.status_code = status_code
    return response


def create_success_response(data, status_code: int = 200):
    response = jsonify({'success': True, 'data': data, 'error': None})
    response.status_code = status_code
    return response


def parse_youtube_id(url: str) -> str | None:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
