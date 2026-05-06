import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # OCR 配置
    BAIDU_OCR_API_KEY: str = os.getenv("BAIDU_OCR_API_KEY", "")
    BAIDU_OCR_SECRET_KEY: str = os.getenv("BAIDU_OCR_SECRET_KEY", "")
    BAIDU_OCR_MODE: str = os.getenv("BAIDU_OCR_MODE", "accurate_basic")
    
    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Embedding 模型配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # 存储配置
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "app/storage")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "app/uploads")
    
    # CORS 配置
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def cors_origin_list(self) -> list:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def artifacts_dir(self) -> str:
        return os.path.join(self.STORAGE_DIR, "artifacts")
    
    @property
    def vectors_dir(self) -> str:
        return os.path.join(self.STORAGE_DIR, "vectors")

settings = Settings()