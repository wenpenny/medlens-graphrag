from app.logger import get_logger
from app.exceptions import AppError
from app.services.deepseek_service import DeepSeekService

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是药品说明书、药盒、手写药方、医嘱纸条的信息抽取助手。
你不是医生，不能诊断，不能推荐新药，不能建议用户自行停药、换药或调整剂量。
你的任务是从输入文本中抽取用于 GraphRAG 查询的结构化药品实体信息。
只输出 JSON，不要输出其他任何文字。

输出格式必须是严格的 JSON：
{
  "items": [
    {
      "drug_name": "药品商品名或通用名",
      "generic_name": "药品通用名",
      "brand_name": "药品商品名",
      "ingredients": ["成分1", "成分2"],
      "indications": ["适应症1", "适应症2"],
      "contraindication_groups": ["禁忌人群1", "禁忌人群2"],
      "caution_groups": ["慎用人群1", "慎用人群2"],
      "dosage": "用法用量（仅从原文提取）",
      "confidence": 0.0-1.0的置信度,
      "uncertain_fields": ["不确定的字段名"]
    }
  ],
  "need_user_confirm": true或false,
  "summary": "提取结果摘要"
}

规则：
1. 仔细分析文本，识别所有药品相关信息
2. dosage 只能来自输入文本，不能编造
3. 如果药名或其他关键信息不确定，need_user_confirm设为true，并在uncertain_fields中列出
4. 如果输入不是药品相关文本，返回空items数组
5. 不能输出诊断或处方建议
6. 如果无法识别任何药品，items为空数组"""

class QueryEntityExtractService:
    def __init__(self):
        self.deepseek = DeepSeekService()
    
    def extract_from_ocr(self, ocr_text: str) -> dict:
        logger.info(f"[QueryExtract] start, ocr_text length={len(ocr_text)}")
        
        if not ocr_text or not ocr_text.strip():
            return {
                "items": [],
                "need_user_confirm": True,
                "summary": "OCR 文本为空，无法抽取药品实体。"
            }
        
        user_prompt = f"""请从以下文本中抽取药品实体信息：

文本内容：
{ocr_text}

请仔细分析文本，提取药品名称、成分、适应症、禁忌人群、慎用人群、用法用量等信息。"""
        
        try:
            result = self.deepseek.chat_json(SYSTEM_PROMPT, user_prompt)
            
            items = result.get("items", [])
            if isinstance(items, dict):
                items = [items]
            
            need_user_confirm = result.get("need_user_confirm", True)
            summary = result.get("summary", "")
            
            logger.info(f"[QueryExtract] DeepSeek extraction success, items={len(items)}, need_user_confirm={need_user_confirm}")
            
            return {
                "items": items,
                "need_user_confirm": need_user_confirm,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"[QueryExtract][ERROR] extraction failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="QUERY_ENTITY_EXTRACT_FAILED",
                message=f"药品实体抽取失败: {str(e)}"
            )