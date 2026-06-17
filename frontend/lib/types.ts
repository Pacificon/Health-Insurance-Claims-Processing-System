export type ClaimCategory =
  | "CONSULTATION"
  | "DIAGNOSTIC"
  | "PHARMACY"
  | "DENTAL"
  | "VISION"
  | "ALTERNATIVE_MEDICINE";

export type DocumentType =
  | "PRESCRIPTION"
  | "HOSPITAL_BILL"
  | "PHARMACY_BILL"
  | "LAB_REPORT"
  | "DIAGNOSTIC_REPORT"
  | "DENTAL_REPORT"
  | "DISCHARGE_SUMMARY";

export type DocumentQuality = "GOOD" | "UNREADABLE";

export type Decision = "APPROVED" | "PARTIAL" | "REJECTED" | "MANUAL_REVIEW";

export type StageStatus = "PASSED" | "FAILED" | "SKIPPED" | "WARNING";

export interface ClaimDocument {
  file_id: string;
  file_name?: string;
  actual_type: DocumentType;
  quality?: DocumentQuality;
  patient_name_on_doc?: string;
  content?: Record<string, unknown>;
}

export interface ClaimSubmission {
  member_id: string;
  policy_id: string;
  claim_category: ClaimCategory;
  treatment_date: string;
  claimed_amount: number;
  documents: ClaimDocument[];
  ytd_claims_amount?: number;
  hospital_name?: string;
  simulate_component_failure?: boolean;
}

export interface StageTrace {
  stage: string;
  status: StageStatus;
  checks: Record<string, unknown>[];
  fields?: Record<string, unknown> | null;
  rule?: string | null;
  detail?: string | null;
  messages: string[];
}

export interface DecisionTrace {
  claim_id: string;
  stages: StageTrace[];
  decision: Decision | null;
  approved_amount: number;
  rejection_reasons: string[];
  confidence_score: number | null;
  components_failed: string[];
  manual_review_recommended: boolean;
  user_message: string | null;
  financial_breakdown?: Record<string, unknown> | null;
  line_item_decisions?: Record<string, unknown>[] | null;
  fraud_signals?: Record<string, unknown>[] | null;
}

export interface PolicySummary {
  policy_id: string;
  policy_name: string;
  insurer: string;
  per_claim_limit: number;
  claim_categories: string[];
  network_hospital_count: number;
  member_count: number;
}

export interface TestCasePreset {
  case_id: string;
  case_name: string;
  input: ClaimSubmission;
}
