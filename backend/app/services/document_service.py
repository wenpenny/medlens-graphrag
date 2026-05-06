import os
import json
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class DocumentService:
    def load_seed_documents(self) -> list:
        logger.info("[Documents] loading documents from data.json")

        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_json_path = os.path.join(current_dir, "data.json")

        if not os.path.exists(data_json_path):
            data_json_path = "data.json"
            current_dir = os.getcwd()
            if not os.path.exists(data_json_path):
                project_root = os.path.dirname(current_dir)
                data_json_path = os.path.join(project_root, "data.json")

        if not os.path.exists(data_json_path):
            raise AppError(
                status_code=404,
                code="NO_DATA_FILE",
                message=f"数据文件不存在: {data_json_path}, 请确保 data.json 在项目根目录下"
            )

        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data_items = json.load(f)

            if not data_items:
                raise AppError(
                    status_code=404,
                    code="EMPTY_DATA_FILE",
                    message="data.json 中没有药品数据"
                )

            documents = []

            for idx, item in enumerate(data_items):
                text = item.get("text", "")
                entities = item.get("entities", [])

                doc_id = f"doc_{idx}"
                doc = {
                    "id": doc_id,
                    "title": f"药品文档_{idx + 1}",
                    "text": text,
                    "source_path": data_json_path,
                    "metadata": {
                        "source": "data_json",
                        "entities": entities
                    }
                }

                documents.append(doc)
                logger.info(f"[Documents] loaded document: {doc_id}, length: {len(text)}")

            logger.info(f"[Documents] total documents: {len(documents)}")
            return documents

        except json.JSONDecodeError as e:
            logger.error(f"[Documents][ERROR] failed to parse data.json: {str(e)}")
            raise AppError(
                status_code=500,
                code="INVALID_DATA_FILE",
                message=f"data.json 格式错误: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[Documents][ERROR] failed to load data.json: {str(e)}")
            raise