from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    dashscope_api_key: str = ""

    database_url: str = "postgresql+asyncpg://voicecal:voicecal@localhost:5432/voicecal"
    redis_url: str = "redis://localhost:6379/0"
    memory_key_prefix: str = "voice_calendar"
    memory_short_ttl_seconds: int = 86400
    memory_agent_name: str = "VoiceCalendarAgent"
    memory_llm_model: str = "qwen3.7-max"
    memory_embedding_model: str = "text-embedding-v3"
    memory_long_term_timeout_seconds: int = 5
    mem0_api_key: str = ""
    mem0_vector_store: str = "milvus"
    mem0_llm_provider: str = ""
    mem0_embedding_provider: str = ""
    mem0_on_disk: bool = False
    milvus_url: str = "http://localhost:19531"
    milvus_token: str = ""
    milvus_db_name: str = ""
    milvus_collection_name: str = "voice_calendar_memories"
    milvus_embedding_dims: int = 1024
    milvus_metric_type: str = "COSINE"

    # WeChat Mini Program
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_subscribe_template_id: str = ""

    # JWT
    jwt_secret: str = "change_me_to_a_random_string_at_least_32_chars"
    jwt_expire_seconds: int = 604800  # 7 days

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
