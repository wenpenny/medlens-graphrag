import os
import uuid
import json
from fastapi import FastAPI, File, UploadFile, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError, app_error_handler, generic_exception_handler
from app.schemas import HealthResponse
from app.services.baidu_ocr_service import BaiduOCRService
from app.services.index_pipeline_service import IndexPipelineService
from app.services.artifact_store_service import ArtifactStoreService
from app.services.vector_store_service import VectorStoreService
from app.services.query_entity_extract_service import QueryEntityExtractService
from app.services.graphrag_service import GraphRAGService

from app.services.deepseek_service import DeepSeekService

logger = get_logger(__name__)

app = FastAPI(title="MedLens GraphRAG", version="1.0.0")

from fastapi import Request

@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    logger.info(f"[HTTP] {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"[HTTP] {request.method} {request.url} - {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

class QueryEntityExtractRequest(BaseModel):
    ocr_text: str

class GraphRAGQueryRequest(BaseModel):
    user_profile: dict
    extracted_items: list

@app.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "app": "MedLens GraphRAG"
    }

@app.post("/api/ocr")
async def ocr_recognize(file: UploadFile = File(...)):
    logger.info(f"[OCR API] Received file: {file.filename}, content_type: {file.content_type}")

    if not file.content_type.startswith("image/"):
        raise AppError(
            status_code=400,
            code="INVALID_FILE_TYPE",
            message="文件类型必须是图片"
        )

    file_ext = os.path.splitext(file.filename)[1]
    new_filename = f"{uuid.uuid4().hex}{file_ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, new_filename)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    logger.info(f"[OCR API] File saved to: {save_path}")

    ocr_service = BaiduOCRService()
    result = ocr_service.recognize(save_path)

    return result

@app.post("/api/index/build")
async def build_index(force: bool = Query(True)):
    logger.info(f"[Index API] build requested, force={force}")
    pipeline = IndexPipelineService()
    result = pipeline.build_index(force=force)
    return result

@app.get("/api/index/status")
async def index_status():
    artifact_store = ArtifactStoreService()
    vector_store = VectorStoreService()

    artifact_names = ["documents", "text_units", "entities", "relationships", "communities", "community_reports", "graph_extract_errors"]
    artifacts_status = {}
    for name in artifact_names:
        exists = artifact_store.exists(name)
        count = artifact_store.count(name) if exists else 0
        artifacts_status[name] = count

    vector_status = vector_store.status()

    return {
        "artifacts": artifacts_status,
        "vector_store": {
            "text_units_exists": vector_status.get("text_units") is not None and vector_status.get("text_units") > 0,
            "text_units_count": vector_status.get("text_units") or 0,
            "entities_exists": vector_status.get("entities") is not None and vector_status.get("entities") > 0,
            "entities_count": vector_status.get("entities") or 0,
            "community_reports_exists": vector_status.get("community_reports") is not None and vector_status.get("community_reports") > 0,
            "community_reports_count": vector_status.get("community_reports") or 0
        }
    }

@app.post("/api/extract-query-entities")
async def extract_query_entities(request: QueryEntityExtractRequest):
    logger.info(f"[Extract Query Entities API] Received request, ocr_text length={len(request.ocr_text)}")
    extract_service = QueryEntityExtractService()
    result = extract_service.extract_from_ocr(request.ocr_text)
    return result

@app.post("/api/graphrag/query")
async def graphrag_query(request: GraphRAGQueryRequest):
    logger.info(f"[GraphRAG API] query request received, items={len(request.extracted_items)}")
    graphrag_service = GraphRAGService()
    result = graphrag_service.query(request.user_profile, request.extracted_items)
    return result


@app.post("/api/scan")
async def scan(
    file: UploadFile = File(...),
    user_profile: str = Form(...)
):
    import time
    start_time = time.time()
    logger.info(f"[API] /api/scan start - filename: {file.filename}, size: {file.size} bytes")
    
    try:
        # 解析 user_profile
        try:
            profile_dict = json.loads(user_profile)
            logger.debug(f"[API] User profile parsed: {json.dumps(profile_dict)}")
        except json.JSONDecodeError as e:
            logger.error(f"[API][ERROR] Invalid user_profile JSON: {str(e)}")
            raise AppError(
                status_code=400,
                code="INVALID_PROFILE",
                message="user_profile 不是有效的 JSON"
            )
        
        # 检查文件类型
        if not file.content_type.startswith("image/"):
            logger.error(f"[API][ERROR] Invalid file type: {file.content_type}")
            raise AppError(
                status_code=400,
                code="INVALID_FILE_TYPE",
                message="文件类型必须是图片"
            )
        
        # 保存图片
        file_ext = os.path.splitext(file.filename)[1]
        new_filename = f"{uuid.uuid4().hex}{file_ext}"
        save_path = os.path.join(settings.UPLOAD_DIR, new_filename)
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(save_path, "wb") as f:
            f.write(await file.read())
        
        logger.info(f"[API] Step 1/4 - Saved upload: {save_path}")
        
        # OCR
        ocr_start = time.time()
        ocr_service = BaiduOCRService()
        ocr_result = ocr_service.recognize(save_path)
        ocr_text = ocr_result.get("ocr_text", "")
        ocr_time = time.time() - ocr_start
        logger.info(f"[API] Step 2/4 - OCR completed in {ocr_time:.2f}s")
        logger.info(f"[API] OCR text length: {len(ocr_text)} chars")
        if ocr_text:
            logger.debug(f"[API] OCR text preview: {ocr_text[:200]}...")
        
        # QueryEntityExtract
        extract_start = time.time()
        extract_service = QueryEntityExtractService()
        extraction_result = extract_service.extract_from_ocr(ocr_text)
        extract_time = time.time() - extract_start
        extracted_items = extraction_result.get("items", [])
        logger.info(f"[API] Step 3/4 - Entity extraction completed in {extract_time:.2f}s")
        logger.info(f"[API] Extracted {len(extracted_items)} entities: {[item.get('entity_name') for item in extracted_items]}")
        
        # GraphRAG Query
        graphrag_start = time.time()
        graphrag_service = GraphRAGService()
        graphrag_result = graphrag_service.query(profile_dict, extracted_items)
        graphrag_time = time.time() - graphrag_start
        logger.info(f"[API] Step 4/4 - GraphRAG query completed in {graphrag_time:.2f}s")
        
        # 检查 GraphRAG 结果
        if graphrag_result:
            risk_count = len(graphrag_result.get("risk_cards", []))
            logger.info(f"[API] GraphRAG result - risk cards: {risk_count}")
            logger.debug(f"[API] GraphRAG result summary: {graphrag_result.get('overall_summary', '')[:200]}...")
        else:
            logger.warning("[API] GraphRAG returned empty result")
        
        # 返回结果
        result = {
            "ocr": ocr_result,
            "extraction": extraction_result,
            "graphrag": graphrag_result
        }
        
        total_time = time.time() - start_time
        logger.info(f"[API] /api/scan completed successfully in {total_time:.2f}s")
        return result
        
    except AppError as e:
        total_time = time.time() - start_time
        logger.error(f"[API][ERROR] {e.code}: {e.detail} (total time: {total_time:.2f}s)")
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[API][ERROR] Unexpected error: {str(e)} (total time: {total_time:.2f}s)")
        import traceback
        logger.error(f"[API][ERROR] Traceback: {traceback.format_exc()}")
        raise AppError(
            status_code=500,
            code="SCAN_FAILED",
            message=f"扫描失败: {str(e)}"
        )

@app.on_event("startup")
async def startup_event():
    logger.info("MedLens GraphRAG backend starting...")
    logger.info("Config loaded.")

    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    storage_dir = os.path.abspath(settings.STORAGE_DIR)

    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(settings.artifacts_dir, exist_ok=True)
    os.makedirs(settings.vectors_dir, exist_ok=True)
    os.makedirs("app/data/seed_documents", exist_ok=True)

    logger.info(f"Upload dir: {upload_dir}")
    logger.info(f"Storage dir: {storage_dir}")
    logger.info("Backend started successfully.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)