from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class ChunkService:
    def chunk_documents(self, documents: list, chunk_size: int = 700, overlap: int = 120) -> list:
        logger.info(f"[Chunking] start, documents: {len(documents)}")
        
        if not documents:
            raise AppError(
                status_code=400,
                code="NO_DOCUMENTS",
                message="没有文档可处理"
            )
        
        text_units = []
        
        for doc in documents:
            doc_id = doc["id"]
            text = doc["text"]
            title = doc["title"]
            metadata = doc.get("metadata", {})
            
            if not text:
                logger.warning(f"[Chunking] document {doc_id} has empty text")
                continue
            
            chunks = self._split_text(text, chunk_size, overlap)
            
            for idx, chunk_text in enumerate(chunks):
                tu_id = f"tu_{doc_id}_{idx}"
                text_unit = {
                    "id": tu_id,
                    "document_id": doc_id,
                    "title": f"{title}_part_{idx}",
                    "text": chunk_text,
                    "n_tokens_est": int(len(chunk_text) / 2),
                    "metadata": metadata.copy()
                }
                text_units.append(text_unit)
            
            logger.info(f"[Chunking] document {doc_id} produced {len(chunks)} chunks")
        
        if not text_units:
            raise AppError(
                status_code=400,
                code="NO_TEXT_UNITS",
                message="没有生成任何 text_units"
            )
        
        logger.info(f"[Chunking] total text_units: {len(text_units)}")
        return text_units
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list:
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            if end < text_length:
                last_period = chunk.rfind("。")
                last_newline = chunk.rfind("\n")
                
                if last_period > chunk_size - 200 and last_period > last_newline:
                    chunk = chunk[:last_period + 1]
                    end = start + len(chunk)
                elif last_newline > chunk_size - 200:
                    chunk = chunk[:last_newline]
                    end = start + len(chunk)
            
            chunks.append(chunk)
            
            if end >= text_length:
                break
            
            start = end - overlap
            
            if start < 0:
                start = 0
        
        return chunks