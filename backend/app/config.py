from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./yibao.db"
    REDIS_URL: str = "redis://localhost:6379"

    # 主力 LLM：aiping 网关（Kimi-K3，OpenAI 兼容）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://aiping.cn/api/v1"
    LLM_MODEL: str = "Kimi-K3"

    # 备选 LLM：阿里云 DashScope（通义千问）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen-plus"
    # 阿里云多模态（视觉）模型：档案管家转录上传的报告图片
    DASHSCOPE_VL_MODEL: str = "qwen-vl-plus"

    # 视觉模型：aiping 网关（GLM-4.6V，供影像/图文理解扩展使用）
    VISION_API_KEY: str = ""
    VISION_BASE_URL: str = "https://aiping.cn/api/v1"
    VISION_MODEL: str = "GLM-4.6V"

    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # 路演离线模式：跳过 LLM/知识库初始化，全程使用关键词+mock降级（无网络依赖）
    DEMO_OFFLINE: bool = False

    # OCR 服务：OCR.space
    OCR_API_KEY: str = ""
    OCR_API_URL: str = "https://api.ocr.space/parse/image"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
