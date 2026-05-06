from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union


class HealthResponse(BaseModel):
    status: str
    app: str


class ErrorResponse(BaseModel):
    error: bool
    code: str
    message: str


class OCRResult(BaseModel):
    success: bool
    text: str
    confidence: Optional[float] = None


class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    pregnancy_status: Optional[str] = None
    chronic_diseases: List[str] = []
    allergies: List[str] = []
    drinking_habit: bool = False
    coffee_habit: bool = False
    grapefruit_habit: bool = False


class DocumentModel(BaseModel):
    id: str
    title: str
    text: str
    source_path: str
    metadata: Dict = {}


class TextUnitModel(BaseModel):
    id: str
    document_id: str
    title: str
    text: str
    n_tokens_est: int
    metadata: Dict = {}


class EntityModel(BaseModel):
    id: str
    title: str
    type: str
    description: str
    text_unit_ids: List[str] = []
    frequency: int = 1


class RelationshipModel(BaseModel):
    id: str
    source: str
    target: str
    type: str
    description: str
    weight: float = 1.0
    text_unit_ids: List[str] = []


class CommunityModel(BaseModel):
    id: str
    level: int = 0
    title: str
    entity_titles: List[str] = []
    relationship_ids: List[str] = []


class CommunityReportModel(BaseModel):
    id: str
    community_id: str
    title: str
    summary: str
    full_content: str
    findings: List[Dict] = []
    risk_keywords: List[str] = []
    entity_titles: List[str] = []


class ExtractedDrugItem(BaseModel):
    drug_name: str = ""
    generic_name: str = ""
    brand_name: str = ""
    ingredients: List[str] = []
    indications: List[str] = []
    contraindication_groups: List[str] = []
    caution_groups: List[str] = []
    dosage: str = ""
    confidence: float = 0.0
    uncertain_fields: List[str] = []


class QueryEntityExtractionResult(BaseModel):
    items: List[ExtractedDrugItem] = []
    need_user_confirm: bool = True
    summary: str = ""


class GraphRAGQueryRequest(BaseModel):
    user_profile: UserProfile
    extracted_items: List[ExtractedDrugItem]


class RiskCard(BaseModel):
    risk_id: str
    risk_type: str
    severity: str
    title: str
    involved_drugs: List[str] = []
    dosage_explanation: str = ""
    reason: str
    graph_evidence: List[str] = []
    text_evidence: List[Dict] = []
    community_evidence: List[Dict] = []
    suggestion: str
    confirm_questions: List[str] = []


class GraphRAGResult(BaseModel):
    extracted_items: List[ExtractedDrugItem] = []
    linked_entities: Dict = {}
    graph_context: Dict = {}
    text_context: Dict = {}
    community_context: Dict = {}
    risk_cards: List[RiskCard] = []
    overall_summary: str = ""
    disclaimer: str = ""


class ScanResponse(BaseModel):
    ocr: Dict = {}
    extraction: QueryEntityExtractionResult = QueryEntityExtractionResult()
    graphrag: GraphRAGResult = GraphRAGResult()