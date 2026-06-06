import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv:
    load_dotenv()

JUDGE0_BASE_URL = os.environ.get("JUDGE0_BASE_URL", "https://judge0-ce.p.rapidapi.com")
JUDGE0_API_KEY = os.environ.get("JUDGE0_API_KEY") or os.environ.get("RAPIDAPI_KEY")
JUDGE0_API_HOST = os.environ.get("JUDGE0_API_HOST", "judge0-ce.p.rapidapi.com")
JUDGE0_TIMEOUT_SECONDS = float(os.environ.get("JUDGE0_TIMEOUT_SECONDS", "20"))
