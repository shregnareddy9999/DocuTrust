import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { resetMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';

const TEST_DOCUMENT_ID = 'doc-demo-0001';
const TEST_VERIFICATION_ID = 'ver-demo-0001';

const testHandlers = [
  ...handlers,
  http.get('*/api/v1/documents/:documentId', ({ params }) => {
    const documentId = String(params.documentId);
    if (documentId === TEST_DOCUMENT_ID) {
      return HttpResponse.json({
        document_id: TEST_DOCUMENT_ID,
        category: 'academic_certificate',
        original_filename: 'marksheet-demo.pdf',
        processing_state: 'UPLOADED',
        uploaded_at: new Date().toISOString(),
      });
    }
    return HttpResponse.json({
      document_id: documentId,
      category: 'academic_certificate',
      original_filename: 'marksheet-demo.pdf',
      processing_state: 'UPLOADED',
      uploaded_at: new Date().toISOString(),
    });
  }),
  http.get('*/api/v1/documents/:documentId/extraction', ({ params }) => {
    const documentId = String(params.documentId);
    return HttpResponse.json({
      document_id: documentId,
      engine_name: 'paddleocr',
      engine_version: '2.8.1',
      extracted_fields: {
        student_name: { value: 'Aarav Demo', confidence: 0.94, source: 'ocr' },
        institution_name: { value: 'Example Technical Institute', confidence: 0.91, source: 'ocr' },
        student_id: { value: 'DEMO-STU-001', confidence: 0.97, source: 'ocr' },
        course_name: { value: 'B.Tech CSE', confidence: 0.88, source: 'ocr' },
        semester_or_year: { value: '5', confidence: 0.83, source: 'ocr' },
        certificate_or_marksheet_id: { value: 'DEMO-MARK-001', confidence: 0.95, source: 'ocr' },
        issue_date: { value: null, confidence: null, source: 'ocr' },
      },
      warnings: [],
      status: 'SUCCEEDED',
    });
  }),
  http.get('*/api/v1/verifications/:verificationId', ({ params }) => {
    const verificationId = String(params.verificationId);
    return HttpResponse.json({
      verification_id: verificationId,
      document_id: TEST_DOCUMENT_ID,
      status: 'VERIFIED_MATCH',
      registry_record_key: 'DEMO-STU-001',
      field_comparisons: [
        { field: 'student_name', extracted_value: 'Aarav Demo', registry_value: 'Aarav Demo', matched: true },
        { field: 'institution_name', extracted_value: 'Example Technical Institute', registry_value: 'Example Technical Institute', matched: true },
        { field: 'student_id', extracted_value: 'DEMO-STU-001', registry_value: 'DEMO-STU-001', matched: true },
        { field: 'course_name', extracted_value: 'B.Tech CSE', registry_value: 'B.Tech CSE', matched: true },
        { field: 'semester_or_year', extracted_value: '5', registry_value: '5', matched: true },
        { field: 'certificate_or_marksheet_id', extracted_value: 'DEMO-MARK-001', registry_value: 'DEMO-MARK-001', matched: true },
      ],
      rule_results: [
        { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
        { rule_id: 'field_match', passed: true, reason: 'All match fields equal registry record DEMO-STU-001' },
      ],
      reason_codes: ['ALL_FIELDS_MATCH'],
      is_current: true,
      supersedes_verification_id: null,
      review_actions: [],
      created_at: new Date().toISOString(),
    });
  }),
  http.get('*/api/v1/verifications/:verificationId/blockchain', ({ params }) => {
    const verificationId = String(params.verificationId);
    return HttpResponse.json({
      verification_id: verificationId,
      recording_status: 'CONFIRMED',
      chain_id: 31337,
      contract_address: '0x5FbDB2315678afecb367f032d93F642f64180aa3',
      transaction_hash: '0x6b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
      event_digest: '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c',
      submitted_at: new Date().toISOString(),
      confirmed_at: new Date().toISOString(),
      error_code: null,
    });
  }),
  http.get('*/api/v1/documents/:documentId/verifications', ({ params }) => {
    const documentId = String(params.documentId);
    return HttpResponse.json({
      document_id: documentId,
      verifications: [
        { verification_id: TEST_VERIFICATION_ID, status: 'VERIFIED_MATCH', is_current: true, supersedes_verification_id: 'ver-demo-0000', review_action_count: 0, created_at: new Date().toISOString() },
        { verification_id: 'ver-demo-0000', status: 'REVIEW_REQUIRED', is_current: false, supersedes_verification_id: null, review_action_count: 1, created_at: new Date(Date.now() - 86400000).toISOString() },
      ],
    });
  }),
];

export const server = setupServer(...testHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  resetMockConfig();
  resetMockCounters();
});
afterAll(() => server.close());

beforeEach(() => {
  resetMockConfig();
  resetMockCounters();
});