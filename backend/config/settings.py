import os
import logging
from dotenv import load_dotenv

# Set up logging for settings module
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Find potential locations for .env files relative to settings.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..'))
root_dir = os.path.abspath(os.path.join(backend_dir, '..'))

env_paths = [
    os.path.join(root_dir, '.env'),
    os.path.join(root_dir, '.env.local'),
    os.path.join(backend_dir, '.env'),
]

for path in env_paths:
    if os.path.exists(path):
        logging.info(f"[Settings] Loading environment variables from: {path}")
        load_dotenv(path)
    else:
        logging.debug(f"[Settings] Env file not found at: {path}")

# Fallback load_dotenv to search current working directory
load_dotenv()


class Settings:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ALLOWED_FILE_EXTENSIONS = {'.pdf', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.webp'}
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
    ]
    
    # Track Flask environment/debug flags
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'


settings = Settings()

# Log configuration diagnostics (without exposing the full API key)
if settings.GEMINI_API_KEY:
    key_preview = f"{settings.GEMINI_API_KEY[:4]}...{settings.GEMINI_API_KEY[-4:]}" if len(settings.GEMINI_API_KEY) > 8 else "too_short"
    logging.info(f"[Settings] GEMINI_API_KEY is configured (Preview: {key_preview}, Length: {len(settings.GEMINI_API_KEY)})")
else:
    logging.warning("[Settings] GEMINI_API_KEY is NOT configured in the environment variables!")

