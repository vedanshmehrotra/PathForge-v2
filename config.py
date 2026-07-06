import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", os.environ.get("PATHFORGE_SECRET_KEY", "dev-secret"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.environ.get("PATHFORGE_DB_PATH", "pathforge.db"))
JWT_SECRET = os.environ.get("JWT_SECRET", os.environ.get("PATHFORGE_JWT_SECRET", "dev-jwt-secret"))

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

