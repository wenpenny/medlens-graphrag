import hashlib
from app.logger import get_logger
from app.exceptions import AppError
from app.services.deepseek_service import DeepSeekService

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是医药知识图谱抽取助手。你不是医生，不能诊断，不能开药。
你要从文本中抽取用于 GraphRAG 的实体和关系。

实体类型只能是：
Drug, Ingredient, DrugClass, Disease, Population, Food, Symptom, Risk, Dosage, Contraindication

关系类型只能是：
CONTAINS, BELONGS_TO_CLASS, TREATS, INTERACTS_WITH, RISK_FOR_DISEASE, CAUTION_FOR, CONTRAINDICATED_FOR, FOOD_CONFLICT_WITH, HAS_DOSAGE

只输出 JSON。

输出格式：
{
  "entities": [
    {
      "title": "",
      "type": "",
      "description": "",
      "source_text_unit_id": ""
    }
  ],
  "relationships": [
    {
      "source": "",
      "target": "",
      "type": "",
      "description": "",
      "weight": 1.0,
      "source_text_unit_id": ""
    }
  ]
}

要求：
- title 用中文标准名
- 不确定不要抽取
- relationship source/target 必须是明确实体
- source_text_unit_id 必须等于当前处理的文本单元ID
- 不输出诊断或处方建议
- 如果没有可抽取的内容，输出空数组"""

class GraphExtractService:
    def __init__(self):
        self.deepseek = DeepSeekService()
    
    def extract_from_text_unit(self, text_unit: dict, schema: dict = None) -> dict:
        tu_id = text_unit.get("id", "")
        text = text_unit.get("text", "")
        
        logger.info(f"[GraphExtract] extracting text_unit id={tu_id}")
        
        user_prompt = f"""文本内容：
{text}

文本单元ID：{tu_id}

请从上述文本中抽取实体和关系。"""
        
        try:
            result = self.deepseek.chat_json(SYSTEM_PROMPT, user_prompt)
            
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])
            
            for ent in entities:
                ent["source_text_unit_id"] = tu_id
            
            for rel in relationships:
                rel["source_text_unit_id"] = tu_id
                if "weight" not in rel:
                    rel["weight"] = 1.0
            
            logger.info(f"[GraphExtract] text_unit id={tu_id} entities={len(entities)} relationships={len(relationships)}")
            
            return {
                "entities": entities,
                "relationships": relationships,
                "text_unit_id": tu_id,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"[GraphExtract][ERROR] text_unit id={tu_id}, error={str(e)}")
            return {
                "entities": [],
                "relationships": [],
                "text_unit_id": tu_id,
                "success": False,
                "error": str(e)
            }
    
    def extract_all(self, text_units: list) -> dict:
        logger.info(f"[GraphExtract] start, text_units={len(text_units)}")
        
        all_entities = []
        all_relationships = []
        errors = []
        
        for tu in text_units:
            result = self.extract_from_text_unit(tu)
            
            if result["success"]:
                all_entities.extend(result["entities"])
                all_relationships.extend(result["relationships"])
            else:
                errors.append({
                    "text_unit_id": result["text_unit_id"],
                    "error": result["error"]
                })
        
        merged_entities = self._merge_entities(all_entities)
        merged_relationships = self._merge_relationships(all_relationships)
        
        logger.info(f"[GraphExtract] merged entities={len(merged_entities)} relationships={len(merged_relationships)} errors={len(errors)}")
        
        if not merged_entities and not merged_relationships:
            raise AppError(
                status_code=500,
                code="GRAPH_EXTRACTION_EMPTY",
                message="实体和关系抽取结果为空"
            )
        
        return {
            "entities": merged_entities,
            "relationships": merged_relationships,
            "errors": errors
        }
    
    def _merge_entities(self, entities: list) -> list:
        entity_map = {}
        
        for ent in entities:
            title = ent.get("title", "").strip()
            ent_type = ent.get("type", "").strip()
            
            if not title or not ent_type:
                continue
            
            key = f"{title}|{ent_type}"
            
            if key not in entity_map:
                ent_id = self._generate_entity_id(title, ent_type)
                entity_map[key] = {
                    "id": ent_id,
                    "title": title,
                    "type": ent_type,
                    "description": ent.get("description", ""),
                    "text_unit_ids": [ent.get("source_text_unit_id", "")],
                    "frequency": 1
                }
            else:
                existing = entity_map[key]
                
                desc = ent.get("description", "")
                if desc and desc not in existing["description"]:
                    if existing["description"]:
                        existing["description"] += "；" + desc
                    else:
                        existing["description"] = desc
                
                tu_id = ent.get("source_text_unit_id", "")
                if tu_id and tu_id not in existing["text_unit_ids"]:
                    existing["text_unit_ids"].append(tu_id)
                
                existing["frequency"] += 1
        
        return list(entity_map.values())
    
    def _merge_relationships(self, relationships: list) -> list:
        rel_map = {}
        
        for rel in relationships:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            rel_type = rel.get("type", "").strip()
            
            if not source or not target or not rel_type:
                continue
            
            key = f"{source}|{target}|{rel_type}"
            
            if key not in rel_map:
                rel_id = self._generate_relation_id(source, target, rel_type)
                rel_map[key] = {
                    "id": rel_id,
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "description": rel.get("description", ""),
                    "weight": rel.get("weight", 1.0),
                    "text_unit_ids": [rel.get("source_text_unit_id", "")]
                }
            else:
                existing = rel_map[key]
                
                desc = rel.get("description", "")
                if desc and desc not in existing["description"]:
                    if existing["description"]:
                        existing["description"] += "；" + desc
                    else:
                        existing["description"] = desc
                
                weight = rel.get("weight", 1.0)
                if weight > existing["weight"]:
                    existing["weight"] = weight
                
                tu_id = rel.get("source_text_unit_id", "")
                if tu_id and tu_id not in existing["text_unit_ids"]:
                    existing["text_unit_ids"].append(tu_id)
        
        return list(rel_map.values())
    
    def _generate_entity_id(self, title: str, ent_type: str) -> str:
        key = f"{title}_{ent_type}"
        hash_val = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
        return f"ent_{hash_val}"
    
    def _generate_relation_id(self, source: str, target: str, rel_type: str) -> str:
        key = f"{source}_{target}_{rel_type}"
        hash_val = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
        return f"rel_{hash_val}"