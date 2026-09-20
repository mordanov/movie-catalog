"""Set required env vars before any bot module imports."""
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "0000000000:test_token_for_tests")
os.environ.setdefault("INITIAL_ADMIN_TELEGRAM_ID", "12345")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault("BOT_SECRET", "test-secret")
