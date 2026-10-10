import { http, HttpResponse, delay } from 'msw';
import type { AadhaarLinkResponse, DocumentType, VerificationStatus } from '../types/api';
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
    label: 'Pan Card',
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

let mockDocumentCounter = 0;
let mockVerificationCounter = 0;

function nextDocumentId(): string {
  mockDocumentCounter += 1;
  return `doc-demo-${mockDocumentCounter.toString().padStart(4, '0')}`;
}

function nextVerificationId(): string {
  mockVerificationCounter += 1;
  return `ver-demo-${mockVerificationCounter.toString().padStart(4, '0')}`;
}

export function resetMockCounters(): void {
  mockDocumentCounter = 0;
  mockVerificationCounter = 0;
}

function baseVerifications() {
  const now = new Date().toISOString();
  return {
    verification_id: nextVerificationId(),
    document_id: nextDocumentId(),
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
    verification_id: nextVerificationId(),
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
        verification_id: nextVerificationId(),
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

function mockAadhaarLinkResponse(): AadhaarLinkResponse {
  return {
    lookup_id: 'aadhaar-link-demo-0001',
    source: 'synthetic-demo',
    reference_detected: true,
    citizen: {
      citizen_ref: 'CIT-10001',
      demo_name: 'Aarav Demo',
      aadhaar_ref: 'AAD-10001',
      masked_aadhaar: 'DEMO-XXXX-0001',
      demo_mobile_placeholder: '9000005001',
    },
    linked_documents: [
      {
        id: 'link-pan-20001',
        document_type: 'PAN',
        document_type_label: 'Permanent Account Number Demo',
        demo_document_ref: 'PAN-20001',
        display_value: 'PAN Card reference: PAN-20001',
        issuer_label: 'Synthetic Tax Registry',
        asset_ref: 'PAN-20001',
        asset_mime_type: 'image/png',
        status_label: 'Linked in synthetic registry',
        demo_mobile_placeholder: null,
      },
      {
        id: 'link-dl-30001',
        document_type: 'DRIVING_LICENSE',
        document_type_label: 'Driving Licence Demo',
        demo_document_ref: 'DL-30001',
        display_value: 'Driving Licence reference: DL-30001',
        issuer_label: 'Synthetic Transport Registry',
        asset_ref: 'DL-30001',
        asset_mime_type: 'application/pdf',
        status_label: 'Linked in synthetic registry',
        demo_mobile_placeholder: null,
      },
      {
        id: 'link-mob-50001',
        document_type: 'MOBILE',
        document_type_label: 'Mobile Connection Demo',
        demo_document_ref: 'MOB-50001',
        display_value: 'Mobile Connection reference: MOB-50001',
        issuer_label: 'Synthetic Telecom Registry',
        asset_ref: null,
        asset_mime_type: null,
        status_label: 'Listed in synthetic registry',
        demo_mobile_placeholder: '9000005001',
      },
    ],
    summary: {
      linked_record_count: 3,
      blockchain_seed: 'local-demo-seed',
      last_sync_label: 'Synthetic demo registry snapshot',
    },
  };
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

    const documentId = nextDocumentId();
    return HttpResponse.json(
      { document_id: documentId, category: 'academic_certificate', processing_state: 'UPLOADED' },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/documents/:documentId`, ({ params }) => {
    const documentId = String(params.documentId);
    return HttpResponse.json({
      document_id: documentId,
      category: 'academic_certificate',
      original_filename: 'marksheet-demo.pdf',
      processing_state: 'UPLOADED',
      uploaded_at: new Date().toISOString(),
    });
  }),

  http.get(`${BASE}/documents/:documentId/extraction`, async ({ params }) => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(900);
    const documentId = String(params.documentId);

    if (mock === 'PROCESSING_FAILED') {
      return HttpResponse.json({
        document_id: documentId,
        engine_name: 'paddleocr',
        engine_version: '2.8.1',
        extracted_fields: {},
        warnings: ['OCR timed out on page 1'],
        status: 'FAILED',
      });
    }

    return HttpResponse.json({
      document_id: documentId,
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

  http.get(`${BASE}/documents/:documentId/file`, () => {
    const png = Uint8Array.from([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
      0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
      0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
      0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
      0xde, 0x00, 0x00, 0x00, 0x0c, 0x49, 0x44, 0x41,
      0x54, 0x08, 0xd7, 0x63, 0xf8, 0xff, 0xff, 0x3f,
      0x00, 0x05, 0xfe, 0x02, 0xfe, 0xdc, 0xcc, 0x59,
      0xe7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e,
      0x44, 0xae, 0x42, 0x60, 0x82,
    ]);
    return new HttpResponse(png, {
      headers: {
        'content-type': 'image/png',
        'content-disposition': 'inline; filename="marksheet-demo.png"',
      },
    });
  }),

  http.delete(`${BASE}/documents/:documentId`, async () => {
    const { err, slow } = getMockConfig();
    if (slow) await delay(400);
    if (err === 'DOCUMENT_HAS_HISTORY') {
      return HttpResponse.json(
        {
          error: {
            code: 'DOCUMENT_HAS_HISTORY',
            message: 'Documents with verification history cannot be deleted.',
          },
        },
        { status: 409 }
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${BASE}/documents/:documentId/verify`, async ({ params }) => {
    const { mock, slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(1200);
    const status = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    const documentId = String(params.documentId);
    return HttpResponse.json({ verification_id: nextVerificationId(), status, document_id: documentId });
  }),

  http.post(`${BASE}/aadhaar-link`, async () => {
    const { err, slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(900);

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
    if (err === 'AADHAAR_DEMO_CARD_REQUIRED') {
      return HttpResponse.json(
        {
          error: {
            code: 'AADHAAR_DEMO_CARD_REQUIRED',
            message: 'Upload a DocuTrust synthetic Aadhaar demo card. Other document types are not accepted on this page.',
          },
        },
        { status: 422 }
      );
    }
    if (err === 'AADHAAR_LINK_UNAVAILABLE') {
      return HttpResponse.json(
        { error: { code: 'AADHAAR_LINK_UNAVAILABLE', message: 'Aadhaar Link demo lookup is not available.' } },
        { status: 503 }
      );
    }

    return HttpResponse.json(mockAadhaarLinkResponse());
  }),

  http.post(`${BASE}/aadhaar-link/:citizenRef/message`, async ({ request, params }) => {
    const { err, slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(700);
    if (!request.headers.get('authorization')) {
      return HttpResponse.json(
        { error: { code: 'AUTH_REQUIRED', message: 'Sign in before sending a reminder.' } },
        { status: 401 }
      );
    }
    if (err === 'SMS_FAILED') {
      return HttpResponse.json({
        citizen_ref: String(params.citizenRef),
        recipient_name: 'Aarav Demo',
        masked_mobile: 'XXXXXX5001',
        sms_status: 'failed',
        voice_status: 'not_attempted',
        message: 'SMS request failed; reminder call was not attempted.',
      });
    }
    if (err === 'VOICE_FAILED') {
      return HttpResponse.json({
        citizen_ref: String(params.citizenRef),
        recipient_name: 'Aarav Demo',
        masked_mobile: 'XXXXXX5001',
        sms_status: 'accepted',
        voice_status: 'failed',
        message: 'SMS request accepted; reminder call request failed.',
      });
    }
    return HttpResponse.json({
      citizen_ref: String(params.citizenRef),
      recipient_name: 'Aarav Demo',
      masked_mobile: 'XXXXXX5001',
      sms_status: 'accepted',
      voice_status: 'initiated',
      message: 'SMS request accepted; reminder call request initiated.',
    });
  }),

  http.get(`${BASE}/aadhaar-link/assets/:assetRef`, ({ params }) => {
    const assetRef = String(params.assetRef);
    if (assetRef === 'DL-30001') {
      return new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]), {
        headers: { 'content-type': 'application/pdf' },
      });
    }
    return new HttpResponse(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), {
      headers: { 'content-type': 'image/png' },
    });
  }),

  http.post(`${BASE}/academic-summary`, async ({ request }) => {
    const { slow, net, err } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(900);
    if (err === 'AI_SUMMARY_UNAVAILABLE') {
      return HttpResponse.json(
        {
          error: {
            code: 'AI_SUMMARY_UNAVAILABLE',
            message: 'Could not generate the academic summary. Confirm that Ollama is running locally.',
          },
        },
        { status: 503 }
      );
    }
    const body = (await request.json()) as { document_ids?: string[] };
    const count = body.document_ids?.length ?? 0;
    return HttpResponse.json({
      summary:
        'Aarav Demo submitted synthetic academic documents for B.Tech CSE. Semester details are available only where they appear in the OCR text.',
      documents_analyzed: count,
      model: 'llama3.2:latest',
    });
  }),

  http.post(`${BASE}/verifications/:verificationId/review`, async ({ request, params }) => {
    const { slow, net } = getMockConfig();
    if (net) return HttpResponse.error();
    if (slow) await delay(600);
    const body = (await request.json()) as { action?: string };
    const action = body.action ?? 'ACCEPT';
    const verificationId = String(params.verificationId);
    const newVerificationId = nextVerificationId();
    if (action === 'CORRECT') {
      return HttpResponse.json(
        { review_action_id: 'rev-demo-0001', new_verification_id: newVerificationId, new_status: 'VERIFIED_MATCH' },
        { status: 201 }
      );
    }
    if (action === 'UNRESOLVED') {
      return HttpResponse.json(
        { review_action_id: 'rev-demo-0001', new_verification_id: verificationId, new_status: 'REVIEW_REQUIRED' },
        { status: 201 }
      );
    }
    return HttpResponse.json(
      { review_action_id: 'rev-demo-0001', new_verification_id: verificationId, new_status: 'VERIFIED_MATCH' },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/verifications/:verificationId`, async ({ params }) => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(600);
    const status = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    const verificationId = String(params.verificationId);
    const verification = generatedMockVerification(status);
    return HttpResponse.json({ ...verification, verification_id: verificationId });
  }),

  http.get(`${BASE}/verifications/:verificationId/blockchain`, async ({ params }) => {
    const { chain, slow } = getMockConfig();
    if (slow) await delay(400);
    const verificationId = String(params.verificationId);
    const blockchain = generatedBlockchain(chain);
    return HttpResponse.json({ ...blockchain, verification_id: verificationId });
  }),

  http.get(`${BASE}/documents/:documentId/verifications`, async ({ params }) => {
    const { mock, slow } = getMockConfig();
    if (slow) await delay(400);
    const currentStatus = (mock ?? 'VERIFIED_MATCH') as VerificationStatus;
    const documentId = String(params.documentId);
    const now = new Date().toISOString();
    const currentVerificationId = nextVerificationId();
    const previousVerificationId = nextVerificationId();
    return HttpResponse.json({
      document_id: documentId,
      verifications: [
        { verification_id: currentVerificationId, status: currentStatus, is_current: true, supersedes_verification_id: previousVerificationId, review_action_count: 0, created_at: now },
        { verification_id: previousVerificationId, status: 'REVIEW_REQUIRED', is_current: false, supersedes_verification_id: null, review_action_count: 1, created_at: new Date(Date.now() - 86400000).toISOString() },
      ],
    });
  }),
];
