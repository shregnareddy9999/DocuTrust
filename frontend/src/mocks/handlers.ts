import { http, HttpResponse, delay } from 'msw';
import type { DocumentType, VerificationStatus } from '../types/api';
import { getMockConfig } from './config';

const BASE = '*/api/v1';

export const mockDocumentTypes: DocumentType[] = [
  {
    category: 'academic_certificate',
    label: 'Academic Certificate',
    fields: [
      { name: 'student_name', label: 'Student Name', type: 'text', required: true, match_field: true },
      { name: 'institution_name', label: 'Institution Name', type: 'text', required: true, match_field: true },
      { name: 'student_id', label: 'Student ID', type: 'text', required: true, match_field: true },
      { name: 'course_name', label: 'Course Name', type: 'text', required: true, match_field: true },
      { name: 'semester_or_year', label: 'Semester or Year', type: 'text', required: true, match_field: true },
      { name: 'certificate_or_marksheet_id', label: 'Certificate / Marksheet ID', type: 'text', required: true, match_field: true },
      { name: 'issue_date', label: 'Issue Date', type: 'date', required: false, match_field: false },
    ],
  },
  {
    category: 'institutional_id',
    label: 'Institutional ID',
    fields: [
      { name: 'holder_name', label: 'Holder Name', type: 'text', required: true, match_field: true },
      { name: 'institution_name', label: 'Institution Name', type: 'text', required: true, match_field: true },
      { name: 'id_number', label: 'ID Number', type: 'text', required: true, match_field: true },
      { name: 'designation_or_role', label: 'Designation or Role', type: 'text', required: false, match_field: false },
      { name: 'valid_until', label: 'Valid Until', type: 'date', required: false, match_field: false },
    ],
  },
  {
    category: 'pan_like_demo',
    label: 'PAN-like Demo Card',
    fields: [
      { name: 'holder_name', label: 'Holder Name', type: 'text', required: true, match_field: true },
      { name: 'demo_pan_code', label: 'Demo PAN Code', type: 'text', required: true, match_field: true },
      { name: 'date_of_birth', label: 'Date of Birth', type: 'date', required: true, match_field: true },
      { name: 'father_or_guardian_name', label: 'Father or Guardian Name', type: 'text', required: false, match_field: false },
    ],
  },
  {
    category: 'government_certificate',
    label: 'Government Certificate',
    fields: [
      { name: 'holder_name', label: 'Holder Name', type: 'text', required: true, match_field: true },
      { name: 'certificate_type_label', label: 'Certificate Type', type: 'text', required: true, match_field: true },
      { name: 'certificate_number', label: 'Certificate Number', type: 'text', required: true, match_field: true },
      { name: 'issuing_authority_label', label: 'Issuing Authority', type: 'text', required: true, match_field: true },
      { name: 'issue_date', label: 'Issue Date', type: 'date', required: false, match_field: false },
    ],
  },
];

const STUB_DOCUMENT_ID = 'doc-demo-0001';
const STUB_VERIFICATION_ID = 'ver-demo-0001';

export { STUB_DOCUMENT_ID, STUB_VERIFICATION_ID };

function baseVerifications() {
  const now = new Date().toISOString();
  return {
    verification_id: STUB_VERIFICATION_ID,
    document_id: STUB_DOCUMENT_ID,
    registry_record_key: null,
    field_comparisons: [],
    rule_results: [],
    reason_codes: [],
    is_current: true,
    supersedes_verification_id: null,
    review_actions: [],
    created_at: now,
  };
}

export function generatedMockVerification(mockStatus: VerificationStatus) {
  const base = baseVerifications();
  const comparisonSet = {
    student_name: { extracted: 'Aarav Demo', registry: 'Aarav Demo' },
    institution_name: { extracted: 'Example Technical Institute', registry: 'Example Technical Institute' },
    student_id: { extracted: 'DEMO-STU-001', registry: 'DEMO-STU-001' },
    course_name: { extracted: 'B.Tech CSE', registry: 'B.Tech CSE' },
    semester_or_year: { extracted: '6', registry: '5' },
    certificate_or_marksheet_id: { extracted: 'DEMO-MARK-001', registry: 'DEMO-MARK-001' },
  };

  switch (mockStatus) {
    case 'VERIFIED_MATCH':
      return {
        ...base,
        status: 'VERIFIED_MATCH',
        registry_record_key: 'DEMO-STU-001',
        field_comparisons: Object.entries(comparisonSet).map(([field, v]) => ({
          field,
          extracted_value: v.extracted,
          registry_value: v.registry,
          matched: true,
        })),
        rule_results: [
          { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
          { rule_id: 'field_match', passed: true, reason: 'All match fields equal registry record DEMO-STU-001' },
        ],
        reason_codes: ['ALL_FIELDS_MATCH'],
      };
    case 'REVIEW_REQUIRED':
      return {
        ...base,
        status: 'REVIEW_REQUIRED',
        field_comparisons: Object.entries(comparisonSet).map(([field, v]) => ({
          field,
          extracted_value: v.extracted,
          registry_value: null,
          matched: false,
        })),
        rule_results: [
          { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
          { rule_id: 'field_match', passed: false, reason: 'Not compared pending human review' },
        ],
        reason_codes: ['REVIEW_REQUIRED:low_confidence:semester_or_year'],
      };
    case 'NO_TRUSTED_RECORD':
      return {
        ...base,
        status: 'NO_TRUSTED_RECORD',
        rule_results: [
          { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
          { rule_id: 'field_match', passed: false, reason: 'No registry record shares the identifying key' },
        ],
        reason_codes: ['NO_TRUSTED_RECORD'],
      };
    case 'INTEGRITY_MISMATCH':
      return {
        ...base,
        status: 'INTEGRITY_MISMATCH',
        registry_record_key: 'DEMO-STU-001',
        field_comparisons: Object.entries(comparisonSet).map(([field, v]) => ({
          field,
          extracted_value: v.extracted,
          registry_value: v.registry,
          matched: field !== 'semester_or_year',
        })),
        rule_results: [
          { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
          { rule_id: 'field_match', passed: false, reason: 'semester_or_year does not match registry record DEMO-STU-001' },
        ],
        reason_codes: ['FIELD_MISMATCH:semester_or_year'],
      };
    case 'PROCESSING_FAILED':
      return {
        ...base,
        status: 'PROCESSING_FAILED',
        reason_codes: ['PROCESSING_FAILED:ocr_error'],
        rule_results: [{ rule_id: 'required_field_presence', passed: false, reason: 'OCR failure prevented extraction' }],
      };
    case 'PENDING':
    default:
      return { ...base, status: 'PENDING' };
  }
}

export function generatedBlockchain(chainFlag: string | null) {
  const base = {
    verification_id: STUB_VERIFICATION_ID,
    chain_id: 31337,
    contract_address: '0x5FbDB2315678afecb367f032d93F642f64180aa3',
  };
  const txHash = '0x6b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2';
  const digest = '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c';

  if (!chainFlag) {
    return {
      ...base,
      recording_status: 'CONFIRMED',
      transaction_hash: txHash,
      event_digest: digest,
      submitted_at: new Date().toISOString(),
      confirmed_at: new Date().toISOString(),
      error_code: null,
    };
  }

  const [state, subCode] = chainFlag.split(':');

  switch (state) {
    case 'NOT_REQUESTED':
      return {
        verification_id: STUB_VERIFICATION_ID,
        recording_status: 'NOT_REQUESTED',
        chain_id: null,
        contract_address: null,
        transaction_hash: null,
        event_digest: null,
        submitted_at: null,
        confirmed_at: null,
        error_code: null,
      };
    case 'PENDING':
      return {
        ...base,
        recording_status: 'PENDING',
        transaction_hash: txHash,
        event_digest: digest,
        submitted_at: new Date().toISOString(),
        confirmed_at: null,
        error_code: null,
      };
    case 'FAILED':
      return {
        ...base,
        recording_status: 'FAILED',
        transaction_hash: subCode === 'RPC_UNAVAILABLE' ? null : txHash,
        event_digest: null,
        submitted_at: subCode === 'RPC_UNAVAILABLE' ? null : new Date().toISOString(),
        confirmed_at: null,
        error_code: subCode ?? 'RPC_UNAVAILABLE',
      };
    default:
      return {
        ...base,
        recording_status: 'CONFIRMED',
        transaction_hash: txHash,
        event_digest: digest,
        submitted_at: new Date().toISOString(),
        confirmed_at: new Date().toISOString(),
        error_code: null,
      };
  }
}

export const handlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({ status: 'ok', database: 'ok', ocr_adapter: 'configured', blockchain: 'enabled' })
  ),

  http.get(`${BASE}/document-types`, async () => {
    const flags = getMockConfig();
    if (flags.slow) await delay(600);
    return HttpResponse.json(mockDocumentTypes);
  }),

  http.post(`${BASE}/documents`, async () => {
    const { err, slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(800);

    if (err === 'FILE_TOO_LARGE') {
      return HttpResponse.json(
        { error: { code: 'FILE_TOO_LARGE', message: 'The file exceeds the maximum upload size of 10 MB.' } },
        { status: 413 }
      );
    }
    if (err === 'UNSUPPORTED_MEDIA_TYPE') {
      return HttpResponse.json(
        { error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: 'This file type is not supported. Use JPEG, PNG, or PDF.' } },
        { status: 415 }
      );
    }
    if (err === 'EMPTY_OR_CORRUPT_FILE') {
      return HttpResponse.json(
        { error: { code: 'EMPTY_OR_CORRUPT_FILE', message: 'The file is empty or could not be read.' } },
        { status: 422 }
      );
    }
    if (err === 'INVALID_CATEGORY') {
      return HttpResponse.json(
        { error: { code: 'INVALID_CATEGORY', message: 'The selected category is not recognised. Choose one of the listed categories.' } },
        { status: 400 }
      );
    }

    return HttpResponse.json(
      { document_id: STUB_DOCUMENT_ID, category: 'academic_certificate', processing_state: 'UPLOADED' },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/documents/:documentId`, ({ params }) => {
    return HttpResponse.json({
      document_id: String(params.documentId),
      category: 'academic_certificate',
      original_filename: 'marksheet-demo.pdf',
      processing_state: 'UPLOADED',
      uploaded_at: new Date().toISOString(),
    });
  }),

  http.get(`${BASE}/documents/:documentId/extraction`, async () => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(900);

    if (mock === 'PROCESSING_FAILED') {
      return HttpResponse.json({
        document_id: STUB_DOCUMENT_ID,
        engine_name: 'paddleocr',
        engine_version: '2.8.1',
        extracted_fields: {},
        warnings: ['OCR timed out on page 1'],
        status: 'FAILED',
      });
    }

    return HttpResponse.json({
      document_id: STUB_DOCUMENT_ID,
      engine_name: 'paddleocr',
      engine_version: '2.8.1',
      extracted_fields: {
        student_name: { value: 'Aarav Demo', confidence: 0.94, source: 'ocr' },
        institution_name: { value: 'Example Technical Institute', confidence: 0.91, source: 'ocr' },
        student_id: { value: 'DEMO-STU-001', confidence: 0.97, source: 'ocr' },
        course_name: { value: 'B.Tech CSE', confidence: 0.88, source: 'ocr' },
        semester_or_year:
          mock === 'INTEGRITY_MISMATCH'
            ? { value: '6', confidence: 0.83, source: 'ocr' }
            : { value: '5', confidence: 0.83, source: 'ocr' },
        certificate_or_marksheet_id: { value: 'DEMO-MARK-001', confidence: 0.95, source: 'ocr' },
        issue_date: { value: null, confidence: null, source: 'ocr' },
      },
      warnings: mock === 'REVIEW_REQUIRED' ? ['low_confidence:semester_or_year'] : [],
      status: 'SUCCEEDED',
    });
  }),

  http.post(`${BASE}/documents/:documentId/verify`, async () => {
    const { mock, slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(1200);
    const status = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    return HttpResponse.json({ verification_id: STUB_VERIFICATION_ID, status, document_id: STUB_DOCUMENT_ID });
  }),

  http.post(`${BASE}/verifications/:verificationId/review`, async ({ request }) => {
    const { slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(600);
    const body = (await request.json()) as { action?: string };
    const action = body.action ?? 'ACCEPT';
    if (action === 'CORRECT') {
      return HttpResponse.json(
        { review_action_id: 'rev-demo-0001', new_verification_id: 'ver-demo-0002', new_status: 'VERIFIED_MATCH' },
        { status: 201 }
      );
    }
    if (action === 'UNRESOLVED') {
      return HttpResponse.json(
        { review_action_id: 'rev-demo-0001', new_verification_id: 'ver-demo-0001', new_status: 'REVIEW_REQUIRED' },
        { status: 201 }
      );
    }
    return HttpResponse.json(
      { review_action_id: 'rev-demo-0001', new_verification_id: 'ver-demo-0001', new_status: 'VERIFIED_MATCH' },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/verifications/:verificationId`, async () => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(600);
    const status = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    return HttpResponse.json(generatedMockVerification(status));
  }),

  http.get(`${BASE}/verifications/:verificationId/blockchain`, async () => {
    const { chain, slow } = getMockConfig();
    if (slow) await delay(400);
    return HttpResponse.json(generatedBlockchain(chain));
  }),

  http.get(`${BASE}/documents/:documentId/verifications`, async () => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(400);
    const currentStatus = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    const now = new Date().toISOString();
    return HttpResponse.json({
      document_id: STUB_DOCUMENT_ID,
      verifications: [
        { verification_id: STUB_VERIFICATION_ID, status: currentStatus, is_current: true, supersedes_verification_id: 'ver-demo-0000', review_action_count: 0, created_at: now },
        { verification_id: 'ver-demo-0000', status: 'REVIEW_REQUIRED', is_current: false, supersedes_verification_id: null, review_action_count: 1, created_at: new Date(Date.now() - 86400000).toISOString() },
      ],
    });
  }),
];