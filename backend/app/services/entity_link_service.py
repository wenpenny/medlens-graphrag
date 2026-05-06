from app.logger import get_logger
from app.services.artifact_store_service import ArtifactStoreService

logger = get_logger(__name__)

class EntityLinkService:
    def __init__(self):
        self.artifact_store = ArtifactStoreService()
    
    def link_entities(self, extracted_items: list) -> dict:
        """
        将抽取的药品实体链接到图谱中的实体
        """
        logger.info(f"[EntityLink] start, items={len(extracted_items)}")
        
        entities = self.artifact_store.load_json("entities")
        entity_titles = {e["title"]: e for e in entities}
        
        linked = {}
        
        for item in extracted_items:
            drug_name = item.get("drug_name", "")
            generic_name = item.get("generic_name", "")
            ingredients = item.get("ingredients", [])
            
            candidates = []
            
            if drug_name:
                if drug_name in entity_titles:
                    candidates.append(entity_titles[drug_name])
                elif generic_name and generic_name in entity_titles:
                    candidates.append(entity_titles[generic_name])
            
            for ingredient in ingredients:
                if ingredient in entity_titles:
                    candidates.append(entity_titles[ingredient])
            
            if candidates:
                linked[drug_name] = candidates
        
        logger.info(f"[EntityLink] linked entities={len(linked)}")
        return linked