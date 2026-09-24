import type { VerificationStatus } from '../types/api';

export const STATUS_EXPLANATIONS: Record<VerificationStatus, string> = {
  PENDING:
    'The comparison is still running. Refresh this page to see the outcome when it completes.',
  VERIFIED_MATCH:
    'The extracted values match the reference for this category in the synthetic demo registry. This is an informational demo outcome — it does not evaluate a real-world document.',
  REVIEW_REQUIRED:
    'The comparison could not decide on its own because a required field was missing, a value was read with low confidence, or the reading was ambiguous. A human should look at the document and record a review.',
  NO_TRUSTED_RECORD:
    'No record in the demo registry shares this document\u2019s identifying key. The demo registry only contains the synthetic examples this project seeds.',
  INTEGRITY_MISMATCH:
    'A demo registry record shares the identifying key, but one or more key fields do not match it. The fields that differ are listed below.',
  PROCESSING_FAILED:
    'The comparison could not be completed because of a technical error (for example, the OCR step or the registry lookup failed). This is not a verdict on the document.',
};