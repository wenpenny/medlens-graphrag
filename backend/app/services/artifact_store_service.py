import os
import json
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class ArtifactStoreService:
    ALLOWED_NAMES = [
        "documents",
        "text_units",
        "entities",
        "relationships",
        "communities",
        "community_reports",
        "graph_extract_errors"
    ]
    
    def __init__(self):
        self._artifacts_dir = settings.artifacts_dir
        os.makedirs(self._artifacts_dir, exist_ok=True)
    
    def _validate_name(self, name: str):
        if name not in self.ALLOWED_NAMES:
            raise AppError(
                status_code=400,
                code="INVALID_ARTIFACT_NAME",
                message=f"无效的 artifact 名称: {name}"
            )
    
    def _get_path(self, name: str) -> str:
        return os.path.join(self._artifacts_dir, f"{name}.json")
    
    def save_json(self, name: str, data: list) -> None:
        self._validate_name(name)
        
        if not isinstance(data, list):
            raise AppError(
                status_code=400,
                code="INVALID_DATA_TYPE",
                message="数据必须是列表类型"
            )
        
        file_path = self._get_path(name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        count = len(data)
        logger.info(f"[Artifacts] saved {name}.json, count={count}")
    
    def load_json(self, name: str) -> list:
        self._validate_name(name)
        
        file_path = self._get_path(name)
        
        if not os.path.exists(file_path):
            raise AppError(
                status_code=404,
                code="ARTIFACT_NOT_FOUND",
                message=f"Artifact 文件不存在: {name}.json"
            )
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = len(data)
        logger.info(f"[Artifacts] loaded {name}.json, count={count}")
        
        return data
    
    def exists(self, name: str) -> bool:
        self._validate_name(name)
        return os.path.exists(self._get_path(name))
    
    def count(self, name: str) -> int:
        if not self.exists(name):
            return 0
        
        data = self.load_json(name)
        return len(data)
    
    def status(self) -> dict:
        status = {}
        for name in self.ALLOWED_NAMES:
            if self.exists(name):
                try:
                    data = self.load_json(name)
                    status[name] = len(data)
                except Exception:
                    status[name] = "error"
            else:
                status[name] = None
        
        return status