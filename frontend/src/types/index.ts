export type InvestigationStatus = 'draft' | 'running' | 'processing' | 'active' | 'completed' | 'archived' | 'failed'

// ---------------------------------------------------------------------------
// Multi-attribute enrichment types (Milestone 1)
// ---------------------------------------------------------------------------

export interface TargetGroupResult {
  label: string         // e.g. "Religion", "Race/Ethnicity", "None"
  detail: string | null // e.g. "Muslim", "Jewish", "LGBTQ+"
  confidence: number    // 0–1 signal density score
}

export interface HarmTypeResult {
  label: string     // e.g. "Dehumanization", "Incitement to Violence", "None"
  confidence: number
}

export interface SeverityRating {
  level: string              // "CRITICAL" | "SEVERE" | "MODERATE" | "LOW" | "MINIMAL"
  score: number              // 0–1 composite score
  recommended_action: string // "AUTO_REMOVE" | "ESCALATE_TO_HUMAN_REVIEW" | etc.
}

export interface EnrichedAnalysis {
  target_group: TargetGroupResult
  harm_type: HarmTypeResult
  severity: SeverityRating
  is_below_threshold: boolean
  threshold_used: number
}

// ---------------------------------------------------------------------------

export interface Investigation {
  id: string
  title: string
  description: string
  keywords: string[]
  languages: string[]
  date_range_start?: string
  date_range_end?: string
  source_types: string[]
  context?: string
  max_collection_size: number
  status: InvestigationStatus
  created_at: string
  updated_at: string
  document_count?: number
  narrative_count?: number
}

export interface InvestigationCreate {
  title: string
  description: string
  keywords: string[]
  languages: string[]
  date_range_start?: string
  date_range_end?: string
  source_types: string[]
  context?: string
  max_collection_size?: number
}

export interface ClassificationResult {
  label: string
  confidence: number
  probabilities: Record<string, number>
  explanation?: string
  flagged_tokens?: string[]
  model_version?: string
}

export interface Document {
  id: string
  investigation_id?: string
  content: string
  source: string
  source_type: string
  author?: string
  url?: string
  published_at?: string
  classification?: ClassificationResult
  needs_review?: boolean
  created_at?: string
}

export interface NarrativeCluster {
  id: string
  investigation_id?: string
  title: string
  description: string
  documents_count: number
  key_phrases: string[]
  sentiment_distribution?: Record<string, number>
  timeline_data?: { date: string; count: number }[]
  source_distribution?: { source: string; count: number }[]
  toxicity_score?: number
  confidence?: number
}

export interface AnalysisRequest {
  text?: string
  image?: File
  image_url?: string
  investigation_id?: string
  model_type?: string
}

export interface AnalysisResponse {
  id: string
  text?: string
  predicted_label?: string
  confidence?: number
  class_probabilities?: Record<string, number>
  explanation?: any
  classification: ClassificationResult
  model_id?: string
  model_version?: string
  is_available?: boolean
  processed_at?: string
  created_at: string
  ocr_text?: string
  vision_results?: {
    description?: string
    detected_objects?: string[]
    safety_ratings?: Record<string, string>
  }
  coordination_score?: number
  enriched?: EnrichedAnalysis | null
  llm_reasoning?: {
    model?: string
    verdict?: string
    targeted_group?: string
    explanation?: string
  } | null
}

export interface ModelStatus {
  name: string
  status: 'loaded' | 'ready' | 'loading' | 'failed' | 'offline'
  device: string
  memory_used_mb: number
  type: string
  latency_ms?: number
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  uptime_seconds: number
  version: string
  models: Record<string, ModelStatus>
  total_investigations?: number
  total_documents?: number
  total_sources?: number
  items_needing_review?: number
  narrative_clusters?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CoordinationIndicator {
  id: string
  investigation_id?: string
  name: string
  description: string
  score: number // 0 to 1
  uncertainty: 'low' | 'medium' | 'high'
  evidence: string[]
  detected_patterns: string[]
  timestamp: string
}

export interface HumanFeedback {
  id: string
  document_id?: string
  text: string
  original_label: string
  corrected_label: string
  confidence_user?: number
  notes?: string
  reviewer?: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

export interface Dataset {
  id: string
  name: string
  description?: string
  row_count: number
  labels_distribution: Record<string, number>
  created_at: string
  file_size?: string
  preview_rows?: Record<string, any>[]
}

export interface EvaluationRun {
  id: string
  model_name: string
  dataset_id: string
  dataset_name?: string
  accuracy: number
  f1_macro: number
  precision_macro: number
  recall_macro: number
  per_class_metrics: Record<string, { precision: number; recall: number; f1: number; support: number }>
  confusion_matrix?: number[][]
  class_names?: string[]
  executed_at: string
}

export interface ScrapedDocument {
  title: string
  url: string
  publisher: string
  published_at?: string
  snippet: string
  source_type: 'newspaper' | 'social_media' | 'web_magazine'
  platform: string
  toxicity?: {
    label: string
    confidence: number
    is_hate: boolean
    is_offensive: boolean
  }
}

export interface GroundedClaim {
  id: string
  claim: string
  verdict: 'verified' | 'debunked' | 'unverified' | 'disputed'
  confidence: number
  supporting_sources: { title: string; url: string; publisher?: string }[]
  contradicting_sources: { title: string; url: string; publisher?: string }[]
  summary: string
}

export interface LiveNarrativeReport {
  query: string
  investigation_id?: string
  target_article?: {
    title: string
    url: string
    publisher: string
    author?: string
    snippet: string
  }
  sources_searched: {
    newspapers: number
    social_media: number
    total_documents: number
  }
  verdict_summary: {
    overall_status: 'verified' | 'debunked' | 'disputed' | 'unverified'
    truth_score: number
    status_description: string
    executive_summary: string
    verified_facts: string[]
    debunked_rumors: string[]
    unresolved_questions: string[]
    claims: GroundedClaim[]
  }
  claims: GroundedClaim[]
  collected_documents: ScrapedDocument[]
  toxicity_overview: {
    hate_count: number
    offensive_count: number
    neutral_count: number
  }
  analyzed_at: string
}
