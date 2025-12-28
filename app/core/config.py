from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'sqlite:///./minddoc.db'       
    jwt_secret: str = 'supersecretkey'
    jwt_algorithm: str = 'HS256'
    jwt_expiration_hours: int = 24
    gemini_api_key: str = ''
    deepseek_api_key: str = ''
    
    # Ollama Configuration
    ollama_api_url: str = 'http://127.0.0.1:11434/api/generate'
    ollama_model: str = 'deepseek-v3.1:671b-cloud'

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()