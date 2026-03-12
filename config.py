import ssl
import os
from dotenv import load_dotenv

ssl._create_default_https_context = ssl._create_unverified_context
load_dotenv(dotenv_path=".env")

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")