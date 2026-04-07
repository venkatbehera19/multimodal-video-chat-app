import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
  """Load and expose environment settings for the application."""

  def __init__(self) -> None:
    self.ENV: str = os.getenv("ENV")
    self.PROJECT_NAME: str = os.getenv("PROJECT_NAME")
    self.PROJECT_VERSION: str = os.getenv("PROJECT_VERSION")
    self.PROJECT_DESCRIPTION: str = os.getenv("PROJECT_DESCRIPTION")

    self.DB_FILE_PATH: str = os.getenv("DB_FILE_PATH")
    self.SQLALCHEMY_DATABASE_URL: str = os.getenv("SQLALCHEMY_DATABASE_URL")

    self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

    working_dir = os.path.abspath(os.getenv("WORKING_DIR", ".").strip() or ".")
    self.WORKING_PROJECT_DIR: str = os.path.join(working_dir,self.PROJECT_NAME)
    self.UPLOAD_DIR: str = str(BASE_DIR / "static" / "upload")

    self.HF_TOKEN: str = os.getenv("HF_TOKEN")
    self.VECTOR_DB_TYPE: str = os.getenv('VECTOR_DB_TYPE')
    self.VECTOR_PERSIST_DIR: str = os.getenv("VECTOR_PERSIST_DIR")
    self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    self.REDIS_HOST: str = os.getenv("REDIS_HOST")
    self.REDIS_PORT: str = os.getenv("REDIS_PORT")
    self.REDIS_DB: str = os.getenv("REDIS_DB")
    self.REDIS_PROTOCOL: str = os.getenv("REDIS_PROTOCOL")
    self.USE_REDIS: str = os.getenv("USE_REDIS")

    self.ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME")
    self.ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL")
    self.ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD")
    self.QDRANT_HOST: str = os.getenv("QDRANT_HOST")
    self.QDRANT_PORT: str = os.getenv("QDRANT_PORT")
    self.QDRANT_PROTOCOL: str = os.getenv("QDRANT_PROTOCOL")
    self.SEMANTIC_CHUNKING: str = os.getenv("SEMANTIC_CHUNKING")
    self.QDRANT_HYBRID_SEARCH: str = os.getenv("QDRANT_HYBRID_SEARCH")
    self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

settings = Settings()