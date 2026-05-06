from app.logger import get_logger
from app.exceptions import AppError
from app.safety import DISCLAIMER
from app.services.artifact_store_service import ArtifactStoreService
from app.services.vector_store_service import VectorStoreService
from app.services.local_search_service import LocalSearchService
from app.services.report_generate_service import ReportGenerateService

logger = get_logger(__name__)

class GraphRAGService:
    def __init__(self):
        self.artifact_store = ArtifactStoreService()
        self.vector_store = VectorStoreService()
        self.local_search = LocalSearchService()
        self.report_generator = ReportGenerateService()
    
    def check_index_ready(self):
        """检查索引是否已构建完成"""
        required_artifacts = ["entities", "relationships", "text_units", "community_reports"]
        
        for artifact in required_artifacts:
            if not self.artifact_store.exists(artifact):
                logger.error(f"[GraphRAG] artifact not found: {artifact}")
                raise AppError(
                    status_code=400,
                    code="INDEX_NOT_READY",
                    message=f"索引未就绪：缺少 {artifact}"
                )
        
        vector_tables = self.vector_store.status()
        required_tables = ["text_units", "entities", "community_reports"]
        
        for table in required_tables:
            if vector_tables.get(table) is None or vector_tables[table] == 0:
                logger.error(f"[GraphRAG] vector table not found or empty: {table}")
                raise AppError(
                    status_code=400,
                    code="INDEX_NOT_READY",
                    message=f"索引未就绪：缺少或为空的向量表 {table}"
                )
        
        logger.info("[GraphRAG] index is ready")
    
    def query(self, user_profile: dict, extracted_items: list) -> dict:
        """执行完整的 GraphRAG 查询流程"""
        logger.info("[GraphRAG] query start")
        
        # 1. 检查索引是否就绪
        self.check_index_ready()
        
        # 2. 本地搜索
        logger.info("[GraphRAG] running local search")
        local_context = self.local_search.search(user_profile, extracted_items)
        
        # 3. 生成报告
        logger.info("[GraphRAG] generating report")
        report = self.report_generator.generate(user_profile, extracted_items, local_context)
        
        # 4. 构造返回结果
        linked_entities_dict = local_context.get("linked_entities", {})
        
        # 转换为前端期望的格式
        query_terms = list(linked_entities_dict.keys())
        linked_entities = []
        unlinked_terms = []
        
        for drug_name, candidates in linked_entities_dict.items():
            for candidate in candidates:
                linked_entities.append({
                    "query": drug_name,
                    "title": candidate.get("title", ""),
                    "type": candidate.get("type", ""),
                    "match_type": "exact" if drug_name == candidate.get("title") else "related",
                    "score": 1.0 if drug_name == candidate.get("title") else 0.8,
                    "need_user_confirm": False
                })
        
        result = {
            "extracted_items": extracted_items,
            "entity_link": {
                "query_terms": query_terms,
                "linked_entities": linked_entities,
                "unlinked_terms": unlinked_terms
            },
            "graph_context": local_context["graph_context"],
            "text_context": local_context["text_context"],
            "community_context": local_context["community_context"],
            "risk_cards": [],  # 保持兼容性
            "overall_summary": report["overall_summary"],
            "disclaimer": report.get("disclaimer", DISCLAIMER)
        }
        
        logger.info("[GraphRAG] query completed")
        return result