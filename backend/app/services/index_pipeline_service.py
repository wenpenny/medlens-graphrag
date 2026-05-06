from app.logger import get_logger
from app.exceptions import AppError
from app.config import settings
from app.services.document_service import DocumentService
from app.services.chunk_service import ChunkService
from app.services.graph_extract_service import GraphExtractService
from app.services.community_service import CommunityService
from app.services.artifact_store_service import ArtifactStoreService
from app.services.vector_store_service import VectorStoreService

logger = get_logger(__name__)

class IndexPipelineService:
    def __init__(self):
        self.doc_service = DocumentService()
        self.chunk_service = ChunkService()
        self.graph_service = GraphExtractService()
        self.community_service = CommunityService()
        self.artifact_store = ArtifactStoreService()
        self.vector_store = VectorStoreService()
    
    def build_index(self, force: bool = True) -> dict:
        logger.info("[Index] build_index started, force=%s", force)
        
        try:
            if force:
                logger.info("[Index] force=True, resetting vector store")
                self.vector_store.reset()
            
            logger.info("[Index] stage=LoadDocuments start")
            documents = self.doc_service.load_seed_documents()
            logger.info("[Index] stage=LoadDocuments success documents=%d", len(documents))
            
            logger.info("[Index] stage=ChunkDocuments start")
            text_units = self.chunk_service.chunk_documents(documents)
            logger.info("[Index] stage=ChunkDocuments success text_units=%d", len(text_units))
            
            logger.info("[Index] stage=ExtractGraph start")
            graph_result = self.graph_service.extract_all(text_units)
            entities = graph_result["entities"]
            relationships = graph_result["relationships"]
            graph_errors = graph_result.get("errors", [])
            logger.info("[Index] stage=ExtractGraph success entities=%d relationships=%d errors=%d",
                       len(entities), len(relationships), len(graph_errors))
            
            logger.info("[Index] stage=DetectCommunities start")
            communities = self.community_service.detect_communities(entities, relationships)
            logger.info("[Index] stage=DetectCommunities success communities=%d", len(communities))
            
            logger.info("[Index] stage=GenerateCommunityReports start")
            community_reports = self.community_service.generate_all_reports(communities, entities, relationships)
            logger.info("[Index] stage=GenerateCommunityReports success reports=%d", len(community_reports))
            
            logger.info("[Index] stage=SaveArtifacts start")
            self.artifact_store.save_json("documents", documents)
            self.artifact_store.save_json("text_units", text_units)
            self.artifact_store.save_json("entities", entities)
            self.artifact_store.save_json("relationships", relationships)
            self.artifact_store.save_json("communities", communities)
            self.artifact_store.save_json("community_reports", community_reports)
            self.artifact_store.save_json("graph_extract_errors", graph_errors)
            logger.info("[Index] stage=SaveArtifacts success")
            
            logger.info("[Index] stage=EmbedAndWriteVectors start")
            self.vector_store.upsert_text_units(text_units)
            self.vector_store.upsert_entities(entities)
            self.vector_store.upsert_community_reports(community_reports)
            vector_status = self.vector_store.status()
            logger.info("[Index] stage=EmbedAndWriteVectors success tables=%s", vector_status)
            
            result = {
                "documents": len(documents),
                "text_units": len(text_units),
                "entities": len(entities),
                "relationships": len(relationships),
                "communities": len(communities),
                "community_reports": len(community_reports),
                "graph_extract_errors": len(graph_errors),
                "vector_store": "lancedb",
                "embedding_model": settings.EMBEDDING_MODEL
            }
            
            logger.info("[Index] build completed: %s", result)
            return result
            
        except AppError as e:
            logger.error("[Index][ERROR] stage=build_index, code=%s, message=%s", e.code, e.detail)
            raise
        except Exception as e:
            logger.error("[Index][ERROR] stage=build_index, code=UNKNOWN, message=%s", str(e))
            raise AppError(
                status_code=500,
                code="INDEX_BUILD_FAILED",
                message=f"索引构建失败: {str(e)}"
            )