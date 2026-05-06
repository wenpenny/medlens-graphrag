from app.logger import get_logger
from app.services.artifact_store_service import ArtifactStoreService
from app.services.vector_store_service import VectorStoreService
from app.services.entity_link_service import EntityLinkService

logger = get_logger(__name__)

class LocalSearchService:
    def __init__(self):
        self.artifact_store = ArtifactStoreService()
        self.vector_store = VectorStoreService()
        self.entity_link = EntityLinkService()
    
    def search(self, user_profile: dict, extracted_items: list) -> dict:
        logger.info("[LocalSearch] start")
        
        # 1. 调用 EntityLinkService.link_entities
        linked_entities = self.entity_link.link_entities(extracted_items)
        
        # 2. 读取 artifacts
        entities = self.artifact_store.load_json("entities")
        relationships = self.artifact_store.load_json("relationships")
        text_units = self.artifact_store.load_json("text_units")
        communities = self.artifact_store.load_json("communities")
        community_reports = self.artifact_store.load_json("community_reports")
        
        # 3. 提取 linked_titles
        linked_titles = set()
        for drug_name, candidates in linked_entities.items():
            for candidate in candidates:
                linked_titles.add(candidate["title"])
        
        logger.info(f"[LocalSearch] linked titles={len(linked_titles)}")
        
        # 4. 收集一跳关系
        one_hop_rels = []
        one_hop_nodes = set(linked_titles)
        
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            if source in linked_titles or target in linked_titles:
                one_hop_rels.append(rel)
                one_hop_nodes.add(source)
                one_hop_nodes.add(target)
        
        logger.info(f"[LocalSearch] one-hop relationships={len(one_hop_rels)}")
        
        # 5. 收集二跳关系
        two_hop_rels = []
        two_hop_nodes = set(one_hop_nodes)
        
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            if (source in one_hop_nodes or target in one_hop_nodes) and rel not in one_hop_rels:
                two_hop_rels.append(rel)
                two_hop_nodes.add(source)
                two_hop_nodes.add(target)
        
        logger.info(f"[LocalSearch] two-hop relationships={len(two_hop_rels)}")
        
        # 6. 构造 query_tags
        query_tags = []
        age = user_profile.get("age", 0)
        if age >= 65:
            query_tags.append("老年人")
        
        pregnancy_status = user_profile.get("pregnancy_status", "")
        if pregnancy_status == "pregnant":
            query_tags.append("孕妇")
        elif pregnancy_status == "lactating":
            query_tags.append("哺乳期")
        
        chronic_diseases = user_profile.get("chronic_diseases", [])
        query_tags.extend(chronic_diseases)
        
        if user_profile.get("drinking_habit", False):
            query_tags.append("酒精")
        if user_profile.get("coffee_habit", False):
            query_tags.append("咖啡")
        if user_profile.get("grapefruit_habit", False):
            query_tags.append("葡萄柚")
            query_tags.append("西柚")
        
        logger.info(f"[LocalSearch] query_tags={query_tags}")

        # 7. 构造 risk_paths
        risk_paths = []
        all_rels = one_hop_rels + two_hop_rels

        # 收集所有实体
        entity_map = {e["title"]: e for e in entities}

        # INTERACTS_WITH: 药物联用风险
        for rel in all_rels:
            if rel.get("type") == "INTERACTS_WITH":
                risk_paths.append({
                    "type": "drug_interaction",
                    "path": [rel["source"], rel["type"], rel["target"]],
                    "description": f"{rel['source']} 与 {rel['target']} 存在相互作用"
                })

        # RISK_FOR_DISEASE: 目标命中慢性病
        for rel in all_rels:
            if rel.get("type") == "RISK_FOR_DISEASE":
                target = rel.get("target", "")
                if target in chronic_diseases:
                    risk_paths.append({
                        "type": "disease_risk",
                        "path": [rel["source"], rel["type"], rel["target"]],
                        "description": f"{rel['source']} 对 {rel['target']} 患者有风险"
                    })

        # FOOD_CONFLICT_WITH: 饮食冲突
        for rel in all_rels:
            if rel.get("type") == "FOOD_CONFLICT_WITH":
                target = rel.get("target", "")
                if target in ["酒精", "咖啡", "葡萄柚", "西柚"]:
                    risk_paths.append({
                        "type": "food_conflict",
                        "path": [rel["source"], rel["type"], rel["target"]],
                        "description": f"{rel['source']} 与 {rel['target']} 存在冲突"
                    })

        # CAUTION_FOR / CONTRAINDICATED_FOR: 人群风险
        for rel in all_rels:
            rel_type = rel.get("type", "")
            if rel_type in ["CAUTION_FOR", "CONTRAINDICATED_FOR"]:
                target = rel.get("target", "")
                if target in query_tags:
                    risk_paths.append({
                        "type": "population_risk",
                        "path": [rel["source"], rel_type, rel["target"]],
                        "description": f"{rel['source']} {rel_type} {rel['target']}"
                    })

        # 重复成分检测
        ingredient_map = {}
        for rel in all_rels:
            if rel.get("type") == "CONTAINS":
                ingredient = rel.get("target", "")
                if ingredient not in ingredient_map:
                    ingredient_map[ingredient] = []
                ingredient_map[ingredient].append(rel["source"])
        
        for ingredient, drugs in ingredient_map.items():
            if len(drugs) >= 2:
                risk_paths.append({
                    "type": "duplicate_ingredient",
                    "path": drugs + ["CONTAINS", ingredient],
                    "description": f"多种药物含有相同成分 {ingredient}: {', '.join(drugs)}"
                })
        
        logger.info(f"[LocalSearch] risk_paths={len(risk_paths)}")
        
        # 8. 收集关系 text_unit_ids
        text_unit_ids = set()
        for rel in all_rels:
            text_unit_id = rel.get("text_unit_id")
            if text_unit_id:
                text_unit_ids.add(text_unit_id)
        
        related_text_units = [tu for tu in text_units if tu["id"] in text_unit_ids]
        logger.info(f"[LocalSearch] related_text_units={len(related_text_units)}")
        
        # 9. 构造 query_text
        query_parts = []
        
        for item in extracted_items:
            query_parts.append(item.get("drug_name", ""))
            query_parts.append(item.get("generic_name", ""))
            query_parts.extend(item.get("ingredients", []))
        
        for drug_name, candidates in linked_entities.items():
            for candidate in candidates:
                query_parts.append(candidate["title"])
        
        query_parts.extend(query_tags)
        
        for risk in risk_paths:
            query_parts.append(risk.get("description", ""))
        
        query_text = " ".join([p for p in query_parts if p])
        
        # 10. 调用向量检索
        vector_text_units = self.vector_store.search_text_units(query_text, top_k=8)
        logger.info(f"[LocalSearch] vector_text_units={len(vector_text_units)}")
        
        vector_community_reports = self.vector_store.search_community_reports(query_text, top_k=5)
        logger.info(f"[LocalSearch] community_reports={len(vector_community_reports)}")
        
        # 收集相关社区报告
        related_community_reports = []
        for report in community_reports:
            community_id = report.get("community_id", "")
            for comm in communities:
                if comm.get("id") == community_id:
                    comm_entity_titles = comm.get("entity_titles", [])
                    if any(title in linked_titles for title in comm_entity_titles):
                        related_community_reports.append(report)
                        break
        
        # 合并社区报告（去重）
        all_community_reports = []
        seen_ids = set()
        
        for report in vector_community_reports + related_community_reports:
            if report.get("id") not in seen_ids:
                seen_ids.add(report["id"])
                all_community_reports.append(report)
        
        logger.info("[LocalSearch] completed")
        
        return {
            "linked_entities": linked_entities,
            "graph_context": {
                "entities": [e for e in entities if e["title"] in two_hop_nodes],
                "relationships": all_rels,
                "risk_paths": risk_paths
            },
            "text_context": {
                "related_text_units": related_text_units,
                "vector_text_units": vector_text_units
            },
            "community_context": {
                "community_reports": all_community_reports[:5]
            },
            "query_tags": query_tags
        }