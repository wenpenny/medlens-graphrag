import os
import json
import lancedb
import pyarrow as pa
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

class VectorStoreService:
    TABLE_NAMES = ["text_units", "entities", "community_reports"]
    
    def __init__(self):
        self._db_path = os.path.join(settings.STORAGE_DIR, "vectors", "lancedb")
        os.makedirs(self._db_path, exist_ok=True)
        self._db = lancedb.connect(self._db_path)
        self._embedding = EmbeddingService()
        logger.info(f"[VectorStore] connected to lancedb at {self._db_path}")
    
    def reset(self):
        logger.info(f"[VectorStore] reset lancedb at {self._db_path}")
        
        for table_name in self.TABLE_NAMES:
            if table_name in self._db.table_names():
                self._db.drop_table(table_name)
                logger.info(f"[VectorStore] dropped table {table_name}")
        
        self._db = lancedb.connect(self._db_path)
    
    def _create_table_if_not_exists(self, name: str, schema: pa.Schema):
        if name not in self._db.table_names():
            self._db.create_table(name, schema=schema)
            logger.info(f"[VectorStore] table {name} created")
    
    def upsert_text_units(self, text_units: list):
        if not text_units:
            return
        
        logger.info(f"[VectorStore] writing text_units count={len(text_units)}")
        
        texts = [tu.get("text", "") for tu in text_units]
        vectors = self._embedding.embed_texts(texts)
        
        records = []
        for tu, vector in zip(text_units, vectors):
            records.append({
                "id": tu.get("id", ""),
                "text": tu.get("text", ""),
                "document_id": tu.get("document_id", ""),
                "title": tu.get("title", ""),
                "vector": vector,
                "metadata_json": json.dumps(tu.get("metadata", {}), ensure_ascii=False)
            })
        
        dim = len(vectors[0])
        schema = pa.schema([
            ("id", pa.string()),
            ("text", pa.string()),
            ("document_id", pa.string()),
            ("title", pa.string()),
            ("vector", pa.list_(pa.float32(), dim)),
            ("metadata_json", pa.string())
        ])
        
        self._create_table_if_not_exists("text_units", schema)
        
        try:
            tbl = self._db.open_table("text_units")
            tbl.add(records)
            logger.info(f"[VectorStore] table text_units created, count={len(records)}")
        except Exception as e:
            logger.error(f"[VectorStore][ERROR] write text_units failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="VECTOR_STORE_WRITE_FAILED",
                message=f"向量数据库写入失败：{str(e)}"
            )
    
    def upsert_entities(self, entities: list):
        if not entities:
            return
        
        logger.info(f"[VectorStore] writing entities count={len(entities)}")
        
        texts = [
            f"{ent.get('title', '')}\n{ent.get('type', '')}\n{ent.get('description', '')}"
            for ent in entities
        ]
        vectors = self._embedding.embed_texts(texts)
        
        records = []
        for ent, vector in zip(entities, vectors):
            records.append({
                "id": ent.get("id", ""),
                "title": ent.get("title", ""),
                "type": ent.get("type", ""),
                "description": ent.get("description", ""),
                "vector": vector,
                "metadata_json": json.dumps({
                    "frequency": ent.get("frequency", 1),
                    "text_unit_ids": ent.get("text_unit_ids", [])
                }, ensure_ascii=False)
            })
        
        dim = len(vectors[0])
        schema = pa.schema([
            ("id", pa.string()),
            ("title", pa.string()),
            ("type", pa.string()),
            ("description", pa.string()),
            ("vector", pa.list_(pa.float32(), dim)),
            ("metadata_json", pa.string())
        ])
        
        self._create_table_if_not_exists("entities", schema)
        
        try:
            tbl = self._db.open_table("entities")
            tbl.add(records)
            logger.info(f"[VectorStore] table entities created, count={len(records)}")
        except Exception as e:
            logger.error(f"[VectorStore][ERROR] write entities failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="VECTOR_STORE_WRITE_FAILED",
                message=f"向量数据库写入失败：{str(e)}"
            )
    
    def upsert_community_reports(self, reports: list):
        if not reports:
            return
        
        logger.info(f"[VectorStore] writing community_reports count={len(reports)}")
        
        texts = [
            f"{r.get('title', '')}\n{r.get('summary', '')}\n{r.get('full_content', '')}"
            for r in reports
        ]
        vectors = self._embedding.embed_texts(texts)
        
        records = []
        for r, vector in zip(reports, vectors):
            records.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "summary": r.get("summary", ""),
                "full_content": r.get("full_content", ""),
                "vector": vector,
                "metadata_json": json.dumps({
                    "community_id": r.get("community_id", ""),
                    "risk_keywords": r.get("risk_keywords", []),
                    "entity_titles": r.get("entity_titles", [])
                }, ensure_ascii=False)
            })
        
        dim = len(vectors[0])
        schema = pa.schema([
            ("id", pa.string()),
            ("title", pa.string()),
            ("summary", pa.string()),
            ("full_content", pa.string()),
            ("vector", pa.list_(pa.float32(), dim)),
            ("metadata_json", pa.string())
        ])
        
        self._create_table_if_not_exists("community_reports", schema)
        
        try:
            tbl = self._db.open_table("community_reports")
            tbl.add(records)
            logger.info(f"[VectorStore] table community_reports created, count={len(records)}")
        except Exception as e:
            logger.error(f"[VectorStore][ERROR] write community_reports failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="VECTOR_STORE_WRITE_FAILED",
                message=f"向量数据库写入失败：{str(e)}"
            )
    
    def _search(self, table_name: str, query: str, top_k: int) -> list:
        if table_name not in self._db.table_names():
            raise AppError(
                status_code=404,
                code="VECTOR_TABLE_NOT_FOUND",
                message=f"表不存在: {table_name}"
            )
        
        logger.info(f"[VectorStore] searching table={table_name}, query={query[:50]}..., top_k={top_k}")
        
        try:
            query_vector = self._embedding.embed_texts([query])[0]
            
            tbl = self._db.open_table(table_name)
            
            results = tbl.search(query_vector).limit(top_k).to_list()
            
            parsed_results = []
            for r in results:
                distance = r.get("_distance", 0)
                score = 1.0 / (1.0 + distance) if distance else 1.0
                
                parsed_results.append({
                    "id": r.get("id", ""),
                    "score": score,
                    "text": r.get("text", r.get("summary", "")),
                    "title": r.get("title", ""),
                    "metadata": json.loads(r.get("metadata_json", "{}"))
                })
            
            logger.info(f"[VectorStore] search success, results={len(parsed_results)}")
            return parsed_results
            
        except Exception as e:
            logger.error(f"[VectorStore][ERROR] search failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="VECTOR_SEARCH_FAILED",
                message=f"向量搜索失败: {str(e)}"
            )
    
    def search_text_units(self, query: str, top_k: int = 5) -> list:
        return self._search("text_units", query, top_k)
    
    def search_entities(self, query: str, top_k: int = 5) -> list:
        return self._search("entities", query, top_k)
    
    def search_community_reports(self, query: str, top_k: int = 3) -> list:
        return self._search("community_reports", query, top_k)
    
    def table_exists(self, name: str) -> bool:
        return name in self._db.table_names()
    
    def status(self) -> dict:
        status = {}
        for table_name in self.TABLE_NAMES:
            if table_name in self._db.table_names():
                try:
                    tbl = self._db.open_table(table_name)
                    status[table_name] = tbl.count_rows()
                except Exception:
                    status[table_name] = "error"
            else:
                status[table_name] = None
        return status