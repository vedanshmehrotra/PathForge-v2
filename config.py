import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", os.environ.get("PATHFORGE_SECRET_KEY", "dev-secret"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.environ.get("PATHFORGE_DB_PATH", "pathforge.db"))
JWT_SECRET = os.environ.get("JWT_SECRET", os.environ.get("PATHFORGE_JWT_SECRET", "dev-jwt-secret"))

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# B6: controlled migration switch. Default OFF — the legacy matcher and legacy
# product behavior are unchanged. When ON, the canonical shadow authority model
# (B5/B5.5) gates product consequences (ELO / gaps / recommendations) via
# pathforge.services.product_eligibility.
SHADOW_AUTHORITY_PRODUCT_GATING = os.environ.get(
    "SHADOW_AUTHORITY_PRODUCT_GATING", ""
).strip().lower() in {"1", "true", "yes", "on"}

