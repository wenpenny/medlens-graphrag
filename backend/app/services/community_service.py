import networkx as nx
from app.logger import get_logger
from app.exceptions import AppError
from app.services.deepseek_service import DeepSeekService

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是医药知识图谱社区报告生成助手。你不是医生，不能诊断，不能开药。
请基于输入的实体和关系，生成用于 GraphRAG 的社区报告。
只输出 JSON。

输出格式：
{
  "title": "",
  "summary": "",
  "findings": [
    {
      "summary": "",
      "explanation": ""
    }
  ],
  "risk_keywords": []
}

要求：
- 只基于输入的实体和关系信息生成报告
- 不编造或新增事实
- 表达时使用"可能"、"需要关注"等谨慎措辞
- 必须包含"请咨询医生或药师确认"
- 不得建议停药、换药或调整剂量"""

class CommunityService:
    def __init__(self):
        self.deepseek = DeepSeekService()
    
    def detect_communities(self, entities: list, relationships: list) -> list:
        logger.info(f"[Community] building graph, entities={len(entities)} relationships={len(relationships)}")

        G = nx.Graph()

        entity_map = {ent["title"]: ent for ent in entities}

        for ent in entities:
            G.add_node(ent["title"], entity_id=ent["id"])

        for rel in relationships:
            source_title = rel.get("source", "")
            target_title = rel.get("target", "")
            weight = rel.get("weight", 1.0)

            if source_title and target_title and source_title in G and target_title in G:
                if G.has_edge(source_title, target_title):
                    G[source_title][target_title]["weight"] += weight
                else:
                    G.add_edge(source_title, target_title, weight=weight, relationship_id=rel["id"])

        logger.info(f"[Community] graph nodes={G.number_of_nodes()} edges={G.number_of_edges()}")

        if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
            raise AppError(
                status_code=500,
                code="COMMUNITY_DETECTION_FAILED",
                message="无法检测社区：图中没有关系"
            )

        try:
            communities_generator = nx.algorithms.community.greedy_modularity_communities(G, weight="weight")
            communities_list = list(communities_generator)
        except Exception as e:
            logger.error(f"[Community][ERROR] community detection failed: {str(e)}")
            raise AppError(
                status_code=500,
                code="COMMUNITY_DETECTION_FAILED",
                message=f"社区检测失败: {str(e)}"
            )

        result_communities = []
        for idx, community in enumerate(communities_list):
            community_nodes = list(community)

            entity_titles = [title for title in community_nodes if title in entity_map]

            relationship_ids = []
            for u, v, data in G.edges(data=True):
                if u in community_nodes and v in community_nodes:
                    rel_id = data.get("relationship_id")
                    if rel_id:
                        relationship_ids.append(rel_id)

            comm_id = f"comm_{idx:03d}"
            result_communities.append({
                "id": comm_id,
                "level": 0,
                "title": f"社区 {idx + 1}",
                "entity_titles": entity_titles,
                "relationship_ids": list(set(relationship_ids))
            })

        logger.info(f"[Community] detected communities={len(result_communities)}")

        return result_communities
    
    def generate_community_report(self, community: dict, entities: list, relationships: list) -> dict:
        entity_map = {ent["title"]: ent for ent in entities}
        
        community_entities = []
        for title in community.get("entity_titles", []):
            if title in entity_map:
                community_entities.append(entity_map[title])
        
        community_rels = []
        rel_source_map = {}
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            if source in community.get("entity_titles", []) and target in community.get("entity_titles", []):
                community_rels.append(rel)
        
        entities_text = "\n".join([
            f"- {e.get('title', '')} ({e.get('type', '')}): {e.get('description', '')}"
            for e in community_entities
        ])
        
        relationships_text = "\n".join([
            f"- {r.get('source', '')} --[{r.get('type', '')}]--> {r.get('target', '')}: {r.get('description', '')}"
            for r in community_rels
        ])
        
        user_prompt = f"""请为以下医药知识图谱社区生成报告：

社区实体：
{entities_text}

社区关系：
{relationships_text}

请生成包含 title、summary、findings 和 risk_keywords 的社区报告。"""
        
        try:
            result = self.deepseek.chat_json(SYSTEM_PROMPT, user_prompt)
            
            full_content = result.get("summary", "")
            if result.get("findings"):
                full_content += "\n\n主要发现：\n"
                for finding in result.get("findings", []):
                    full_content += f"- {finding.get('summary', '')}: {finding.get('explanation', '')}\n"
            
            findings = result.get("findings", [])
            if isinstance(findings, dict):
                findings = [findings]
            
            return {
                "id": f"cr_{community['id']}",
                "community_id": community["id"],
                "title": result.get("title", community["title"]),
                "summary": result.get("summary", ""),
                "full_content": full_content,
                "findings": findings,
                "risk_keywords": result.get("risk_keywords", []),
                "entity_titles": community.get("entity_titles", [])
            }
            
        except Exception as e:
            logger.error(f"[Community][ERROR] report generation failed for {community['id']}: {str(e)}")
            raise AppError(
                status_code=500,
                code="COMMUNITY_REPORT_GENERATION_FAILED",
                message=f"社区报告生成失败: {str(e)}"
            )
    
    def generate_all_reports(self, communities: list, entities: list, relationships: list) -> list:
        reports = []
        errors = []
        
        for community in communities:
            try:
                report = self.generate_community_report(community, entities, relationships)
                reports.append(report)
            except Exception as e:
                logger.error(f"[Community][ERROR] failed to generate report for community {community['id']}: {str(e)}")
                errors.append({
                    "community_id": community["id"],
                    "error": str(e)
                })
        
        if not reports:
            raise AppError(
                status_code=500,
                code="COMMUNITY_REPORT_EMPTY",
                message="没有生成任何社区报告"
            )
        
        logger.info(f"[Community] generated {len(reports)} reports, {len(errors)} errors")
        
        return reports