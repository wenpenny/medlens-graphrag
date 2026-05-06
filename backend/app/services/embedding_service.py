import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class EmbeddingService:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance
    
    def _load_model(self):
        model_name = settings.EMBEDDING_MODEL or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
        logger.info(f"[Embedding] loading model: {model_name}")
        
        try:
            self._model = SentenceTransformer(model_name)
            logger.info("[Embedding] model loaded successfully")
        except Exception as e:
            logger.error(f"[Embedding][ERROR] model load failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="EMBEDDING_MODEL_LOAD_FAILED",
                message=f"Embedding 模型加载失败: {str(e)}"
            )
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        
        logger.info(f"[Embedding] encoding texts count={len(texts)}")
        
        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            result = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
            
            dim = len(result[0]) if result else 0
            logger.info(f"[Embedding] encoding success, dim={dim}")
            
            return result
        
        except Exception as e:
            logger.error(f"[Embedding][ERROR] encoding failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="EMBEDDING_ENCODE_FAILED",
                message=f"Embedding 编码失败: {str(e)}"
            )