import os
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'), override=True)

class Settings(BaseSettings):
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./minddoc.db')
    jwt_secret: str = os.getenv('JWT_SECRET', 'supersecretkey')
    jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
    jwt_expiration_hours: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
    deepseek_api_key: str = os.getenv('DEEPSEEK_API_KEY', '')
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    ollama_api_url: str = os.getenv('OLLAMA_API_URL', 'http://127.0.0.1:11434/api/generate')
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'gpt-oss:120b-cloud')

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()