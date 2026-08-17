import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM 配置
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Flask 配置
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # 路径配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    CACHE_DIR = os.path.join(BASE_DIR, "cache")

    # 抓取配置
    MAX_REVIEWS_PER_APP = 500  # 最多抓取多少条评论
    REQUEST_DELAY = 1.0  # 请求间隔（秒），避免被限流

    @classmethod
    def has_llm(cls):
        """检查是否配置了有效的 LLM API Key"""
        return bool(cls.LLM_API_KEY) and cls.LLM_API_KEY != "your_api_key_here"
