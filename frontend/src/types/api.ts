export interface DocumentTypeField {
  name: string;
  label: string;
  type: 'text' | 'date' | 'integer';
  required: boolean;
  match_field: boolean;
}

export interface DocumentType {
  category: string;
  label: string;
  fields: DocumentTypeField[];
}

export interface UploadResponse {
  document_id: string;
  category: string;
  processing_state: 'UPLOADED' | 'OCR_IN_PROGRESS' | 'OCR_DONE' | 'OCR_FAILED';
}

export interface Document {
  document_id: string;
  category: string;
  original_filename: string;
  processing_state: 'UPLOADED' | 'OCR_IN_PROGRESS' | 'OCR_DONE' | 'OCR_FAILED';
  uploaded_at: string;
}

export interface ExtractedField {
  value: string | null;
  confidence: number | null;
  source: 'ocr' | 'corrected';
}

export interface ExtractionResponse {
  document_id: string;
  engine_name: string;
  engine_version: string;
  extracted_fields: Record<string, ExtractedField>;
  warnings: string[];
  status: 'SUCCEEDED' | 'FAILED';
}

export interface FieldComparison {
  field: string;
  extracted_value: string | null;
  registry_value: string | null;
  matched: boolean;
}

export interface RuleResult {
  rule_id: string;
  passed: boolean;
  reason: string;
}

export interface ReviewAction {
  review_action_id: string;
  reviewer_ref: string;
  action: 'ACCEPT' | 'CORRECT' | 'UNRESOLVED';
  corrections: Record<string, string>;
  comment: string;
  created_at: string;
}

export interface VerificationResponse {
  verification_id: string;
  document_id: string;
  status: VerificationStatus;
  registry_record_key: string | null;
  field_comparisons: FieldComparison[];
  rule_results: RuleResult[];
  reason_codes: string[];
  is_current: boolean;
  supersedes_verification_id: string | null;
  review_actions: ReviewAction[];
  created_at: string;
}

export type VerificationStatus =
  | 'PENDING'
  | 'VERIFIED_MATCH'
  | 'REVIEW_REQUIRED'
  | 'NO_TRUSTED_RECORD'
  | 'INTEGRITY_MISMATCH'
  | 'PROCESSING_FAILED';

export interface VerificationHistoryItem {
  verification_id: string;
  status: VerificationStatus;
  is_current: boolean;
  supersedes_verification_id: string | null;
  review_action_count: number;
  created_at: string;
}

export interface VerificationHistoryResponse {
  document_id: string;
  verifications: VerificationHistoryItem[];
}

export interface ReviewRequest {
  reviewer_ref: string;
  action: 'ACCEPT' | 'CORRECT' | 'UNRESOLVED';
  corrections?: Record<string, string>;
  comment: string;
}

export interface ReviewResponse {
  review_action_id: string;
  new_verification_id: string;
  new_status: VerificationStatus;
}

export type BlockchainStatus = 'NOT_REQUESTED' | 'PENDING' | 'CONFIRMED' | 'FAILED';

export interface BlockchainResponse {
  verification_id: string;
  recording_status: BlockchainStatus;
  chain_id: number | null;
  contract_address: string | null;
  transaction_hash: string | null;
  event_digest: string | null;
  submitted_at: string | null;
  confirmed_at: string | null;
  error_code: BlockchainErrorCode | null;
}

export type BlockchainErrorCode =
  | 'RPC_UNAVAILABLE'
  | 'TX_REVERTED'
  | 'RECEIPT_TIMEOUT'
  | 'EVENT_MISMATCH';

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface HealthResponse {
  status: 'ok';
  database: 'ok';
  ocr_adapter: 'configured';
  blockchain: 'enabled' | 'disabled';
}