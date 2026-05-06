export interface HealthResponse {
  status: string;
  app: string;
}

export interface ArtifactStatus {
  exists: boolean;
  count: number;
}

export interface IndexStatus {
  artifacts: {
    documents: number;
    text_units: number;
    entities: number;
    relationships: number;
    communities: number;
    community_reports: number;
    graph_extract_errors?: number;
  };
  vector_store: {
    text_units_exists: boolean;
    text_units_count: number;
    entities_exists: boolean;
    entities_count: number;
    community_reports_exists: boolean;
    community_reports_count: number;
  };
}

export interface UserProfile {
  age: number;
  gender: 'male' | 'female';
  pregnancy_status: 'none' | 'pregnant' | 'lactating';
  chronic_diseases: string[];
  allergies: string[];
  drinking_habit: boolean;
  coffee_habit: boolean;
  grapefruit_habit: boolean;
}

export interface OCRResult {
  source: string;
  need_manual_input: boolean;
  text: string;
  confidence: number;
  words: { text: string; confidence: number }[];
}

export interface ExtractedItem {
  drug_name: string;
  generic_name: string;
  brand_name: string;
  ingredients: string[];
  indications: string[];
  contraindication_groups: string[];
  caution_groups: string[];
  dosage: string;
  confidence: number;
  uncertain_fields: string[];
}

export interface ExtractionResult {
  items: ExtractedItem[];
  need_user_confirm: boolean;
  summary: string;
}

export interface LinkedEntity {
  query: string;
  title: string;
  type: string;
  match_type: string;
  score: number;
  need_user_confirm: boolean;
}

export interface EntityLinkResult {
  query_terms: string[];
  linked_entities: LinkedEntity[];
  unlinked_terms: string[];
}

export interface Entity {
  id: string;
  title: string;
  entity_type: string;
  description?: string;
}

export interface Relationship {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  weight: number;
  description?: string;
}

export interface RiskPath {
  type: string;
  path_steps: { source: string; relation: string; target: string }[];
  description: string;
  severity: 'high' | 'medium' | 'low';
}

export interface GraphContext {
  entities: Entity[];
  relationships: Relationship[];
  risk_paths: RiskPath[];
}

export interface TextUnit {
  id: string;
  document_id: string;
  title: string;
  text: string;
  chunk_index: number;
  score?: number;
  distance?: number;
}

export interface TextContext {
  related_text_units: TextUnit[];
  vector_text_units: TextUnit[];
}

export interface CommunityReport {
  id: string;
  community_id: string;
  title: string;
  summary: string;
  full_content: string;
  findings: { summary: string; explanation: string }[];
  risk_keywords: string[];
  entity_titles: string[];
}

export interface CommunityContext {
  community_reports: CommunityReport[];
}

export interface RiskCard {
  risk_id: string;
  risk_type: string;
  severity: 'high' | 'medium' | 'low';
  title: string;
  involved_drugs: string[];
  dosage_explanation: string;
  reason: string;
  graph_evidence: string[];
  text_evidence: string[];
  community_evidence: string[];
  suggestion: string;
  confirm_questions: string[];
}

export interface GraphRAGResult {
  extracted_items: ExtractedItem[];
  entity_link: EntityLinkResult;
  graph_context: GraphContext;
  text_context: TextContext;
  community_context: CommunityContext;
  risk_cards: RiskCard[];
  overall_summary: string;
  disclaimer: string;
}

export interface ScanResult {
  ocr: OCRResult;
  extraction: ExtractionResult;
  graphrag: GraphRAGResult;
}

export interface APIError {
  code: string;
  message: string;
}

export const CHRONIC_DISEASE_OPTIONS = [
  '高血压',
  '糖尿病',
  '胃病/消化道溃疡',
  '肾功能异常',
  '肝功能异常',
  '心血管疾病',
  '哮喘'
];