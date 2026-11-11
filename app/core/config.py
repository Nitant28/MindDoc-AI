import logging
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_SECRETS = {"", "supersecretkey", "your-random-secret-key-min-32-chars"}


class Settings(BaseSettings):
    # --- Core -----------------------------------------------------------------
    environment: str = "development"
    database_url: str = "sqlite:///./minddoc.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    max_upload_mb: int = 50
    max_pdf_pages: int = 500
    max_image_pixels: int = 40_000_000
    max_docx_uncompressed_mb: int = 200
    rate_auth_per_min: int = 10        # login/register attempts per IP
    rate_upload_per_min: int = 30
    rate_query_per_min: int = 60
    rate_eval_per_min: int = 5
    storage_dir: str = "./data/uploads"  # originals, for pixel-level citations
    # PostgreSQL (ADR-0002): connections switch to this non-owner role so row-level security applies.
    db_app_role: str = "minddoc_app"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # Background processing (ADR-0003/0013): embedded worker threads in the web process (demo hosts), or a separate
    # `python -m app.worker` process. Async ingestion returns immediately and processes the upload in a job.
    embedded_worker: bool = True
    worker_threads: int = 1
    async_ingestion: bool = True

    # --- Auth -----------------------------------------------------------------
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # --- LLM providers (first available in LLM_PROVIDER_ORDER wins) -----------
    llm_provider_order: str = "anthropic,openai,openrouter,gemini,deepseek,ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_fast_model: str = "claude-haiku-5-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    ollama_api_url: str = "http://127.0.0.1:11434/api/generate"
    ollama_model: str = "llama3.1"
    llm_timeout_s: int = 90

    # --- Retrieval / ML -------------------------------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_reranker: bool = True
    # Claim verifier v2: value checks and wording heuristics always run (no models needed). The optional NLI token
    # classifier (LettuceDetect weights, MIT; needs the ML extras, downloads ~275 MB on first start) is off by
    # default: on the held-out test split of benchmarks/hallucination it caught no extra errors and added false flags.
    enable_nli_verifier: bool = False
    verifier_nli_model: str = "KRLabsOrg/tinylettuce-ettin-68m-en"
    # Flag a sentence when the model's max "unsupported" token probability reaches this. Chosen on the dev split of
    # benchmarks/hallucination (lower values added many false flags on correct paraphrases).
    verifier_nli_threshold: float = 0.95
    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 8
    retrieval_candidates: int = 40
    context_char_budget: int = 14000

    # --- Vision ---------------------------------------------------------------
    ocr_engine_order: str = "tesseract,easyocr"
    tesseract_cmd: str = ""
    enable_vision_captions: bool = True
    pdf_ocr_dpi_scale: float = 2.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def provider_order(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_provider_order.split(",") if p.strip()]


settings = Settings()

if settings.jwt_secret in _INSECURE_SECRETS:
    # Never run with a guessable signing key. A random key means tokens reset on restart,
    # which is the safe failure mode; set JWT_SECRET in .env for persistent sessions.
    settings.jwt_secret = secrets.token_hex(32)
    logger.warning("JWT_SECRET not set (or insecure) - using an ephemeral random key. Set JWT_SECRET in .env.")
