"""Central settings (pydantic-settings). Everything comes from Project4/.env.

Integrations not wired up yet (AWS, Pinecone, DB) are Optional so the app
boots today; adapters fail fast with APIKeyMissingError when actually used.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigError

# config.py is at src/app/core/config.py -> parents[3] == Project4/
BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / ".env"


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(_Base):
    url: SecretStr = Field(validation_alias="DATABASE_URL")
    echo: bool = Field(default=False, validation_alias="DB_ECHO")
    pool_size: int = Field(default=5, validation_alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=5, validation_alias="DB_MAX_OVERFLOW")


class ProviderEnum(str, Enum):
    VERCEL = "vercel"
    AWS = "aws"
    PINECONE = "pinecone"


class VercelSettings(_Base):
    base_url: str = Field(
        default="https://ai-gateway.vercel.sh/v1",
        validation_alias="VERCEL_BASE_URL",
    )
    api_key: Optional[SecretStr] = Field(
        default=None, validation_alias="VERCEL_API_KEY"
    )


class LangChainSettings(_Base):
    tracing_v2: bool = Field(default=False, validation_alias="LANGCHAIN_TRACING_V2")
    api_key: Optional[SecretStr] = Field(
        default=None, validation_alias="LANGCHAIN_API_KEY"
    )


class PineconeSettings(_Base):
    api_key: Optional[SecretStr] = Field(
        default=None, validation_alias="PINECONE_API_KEY"
    )
    index_name: Optional[str] = Field(
        default=None, validation_alias="PINECONE_INDEX_NAME"
    )
    namespace: str = Field(
        default="", validation_alias="PINECONE_NAMESPACE"
    )  # optional partition
    environment: str = Field(
        default="", validation_alias="PINECONE_ENVIRONMENT"
    )  # legacy (pod) — unused for serverless
    dimension: int = Field(default=1024, validation_alias="PINECONE_DIMENSION")
    cloud: str = Field(default="aws", validation_alias="PINECONE_CLOUD")
    region: str = Field(default="us-east-1", validation_alias="PINECONE_REGION")
    read_timeout: int = Field(default=180, validation_alias="PINECONE_READ_TIMEOUT")


class AWSSettings(_Base):
    access_key_id: Optional[str] = Field(
        default=None, validation_alias="AWS_ACCESS_KEY_ID"
    )
    secret_access_key: Optional[SecretStr] = Field(
        default=None, validation_alias="AWS_SECRET_ACCESS_KEY"
    )
    region: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    s3_bucket_name: Optional[str] = Field(
        default=None, validation_alias="AWS_S3_BUCKET_NAME"
    )
    presign_expiry: int = Field(default=3600, validation_alias="S3_PRESIGN_EXPIRY")


class ChunkSettings(_Base):
    size: int = Field(default=500, validation_alias="CHUNK_SIZE")
    overlap: int = Field(default=50, validation_alias="CHUNK_OVERLAP")


class RetrievalSettings(_Base):
    default_k: int = Field(default=4, validation_alias="DEFAULT_RETRIEVAL_K")
    hybrid_fetch_k: int = Field(default=20, validation_alias="HYBRID_FETCH_K")
    use_reranker: bool = Field(default=True, validation_alias="USE_RERANKER")
    reranker_model: str = Field(default="", validation_alias="RERANKER_MODEL")
    similarity_threshold: float = Field(
        default=0.70, validation_alias="SIMILARITY_THRESHOLD"
    )


class ChatSettings(_Base):
    """Chat / RAG pipeline knobs."""

    history_turns: int = Field(default=6, validation_alias="CHAT_HISTORY_TURNS")
    rewrite_followup: bool = Field(
        default=True, validation_alias="CHAT_REWRITE_FOLLOWUP"
    )
    max_answer_chars: int = Field(
        default=2000, validation_alias="CHAT_MAX_ANSWER_CHARS"
    )
    no_evidence_message: str = Field(
        default="I could not find supporting evidence in the available documents.",
        validation_alias="CHAT_NO_EVIDENCE_MSG",
    )


class GuardrailSettings(_Base):
    """Input/output guardrail configuration.

    Guards run in parallel by default. Add new guards in the factory registry,
    then list their names here via INPUT_GUARDS / OUTPUT_GUARDS (CSV).
    """

    enabled: bool = Field(default=True, validation_alias="GUARDRAILS_ENABLED")
    parallel: bool = Field(default=True, validation_alias="GUARDRAILS_PARALLEL")
    input_guards: str = Field(
        default="pii,injection,toxicity", validation_alias="INPUT_GUARDS"
    )
    output_guards: str = Field(
        default="pii,system_prompt_leak", validation_alias="OUTPUT_GUARDS"
    )
    pii_block_input: bool = Field(default=False, validation_alias="PII_BLOCK_INPUT")
    pii_block_output: bool = Field(default=True, validation_alias="PII_BLOCK_OUTPUT")
    toxicity_banned_words: str = Field(
        default="", validation_alias="TOXICITY_BANNED_WORDS"
    )  # CSV


class AccessControlSettings(_Base):
    """Tenant / group / subject access filter for vector-store queries.

    Disabled by default — enable once ingestion tags chunks with tenant_id.
    """

    enabled: bool = Field(default=False, validation_alias="ACCESS_CONTROL_ENABLED")


class AppSettings(_Base):
    # --- providers used today (sensible defaults, .env overrides) ---
    embedding_provider: ProviderEnum = Field(
        default=ProviderEnum.VERCEL, validation_alias="EMBEDDING_PROVIDER"
    )
    embedding_model: str = Field(
        default="cohere/embed-v4.0", validation_alias="EMBEDDING_MODEL"
    )
    embedding_dimensions: int = Field(
        default=1024, validation_alias="EMBEDDING_DIMENSIONS"
    )

    llm_provider: ProviderEnum = Field(
        default=ProviderEnum.VERCEL, validation_alias="LLM_PROVIDER"
    )
    llm_model: str = Field(default="openai/gpt-4o-mini", validation_alias="LLM_MODEL")

    vercel: VercelSettings = Field(default_factory=VercelSettings)
    langchain: LangChainSettings = Field(default_factory=LangChainSettings)

    # --- not wired up yet: optional so the app still boots ---
    database_url: Optional[SecretStr] = Field(
        default=None, validation_alias="DATABASE_URL"
    )
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    chunk: ChunkSettings = Field(default_factory=ChunkSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    vector_store_provider: ProviderEnum = Field(
        default=ProviderEnum.PINECONE, validation_alias="VECTOR_STORE_PROVIDER"
    )
    storage_provider: ProviderEnum = Field(
        default=ProviderEnum.AWS, validation_alias="STORAGE_PROVIDER"
    )

    # --- chat pipeline ---
    chat: ChatSettings = Field(default_factory=ChatSettings)
    guardrails: GuardrailSettings = Field(default_factory=GuardrailSettings)
    access_control: AccessControlSettings = Field(default_factory=AccessControlSettings)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Cached accessor. Call this everywhere instead of importing a global."""
    try:
        return AppSettings()
    except Exception as e:  # fail fast with a readable message
        raise ConfigError(f"Invalid configuration: {e}") from e
