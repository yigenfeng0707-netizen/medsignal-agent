from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./yibao.db"
    REDIS_URL: str = "redis://localhost:6379"

    # 主力 LLM：商汤日日新 SenseNova
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://token.sensenova.cn/v1"
    LLM_MODEL: str = "sensenova-6.7-flash-lite"

    # 备选 LLM：阿里云 DashScope（通义千问）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen-plus"

    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # OCR 服务：OCR.space
    OCR_API_KEY: str = ""
    OCR_API_URL: str = "https://api.ocr.space/parse/image"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
