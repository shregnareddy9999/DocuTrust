import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { getDocumentTypes } from '../api/documentTypes';
import { uploadDocument } from '../api/documents';
import { startVerification, getBlockchain } from '../api/verifications';
import { ApiError } from '../api/client';
import { server } from '../test/setup';
import { setMockConfig } from '../mocks/config';
import { STUB_DOCUMENT_ID, STUB_VERIFICATION_ID } from '../mocks/handlers';

describe('API client', () => {
  it('parses the error envelope into a typed ApiError', async () => {
    server.use(
      http.post('*/api/v1/documents', () =>
        HttpResponse.json(
          { error: { code: 'FILE_TOO_LARGE', message: 'The file exceeds the maximum upload size.', details: {} } },
          { status: 413 }
        )
      )
    );
    const file = new File(['x'], 'big.pdf', { type: 'application/pdf' });
    await expect(uploadDocument(file, 'academic_certificate')).rejects.toMatchObject({
      code: 'FILE_TOO_LARGE',
      status: 413,
    });
  });

  it('preserves the server message on the thrown error', async () => {
    server.use(
      http.get('*/api/v1/document-types', () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'Unexpected failure', details: { correlation_id: 'abc' } } },
          { status: 500 }
        )
      )
    );
    try {
      await getDocumentTypes();
      expect.fail('expected reject');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.code).toBe('INTERNAL_ERROR');
      expect(apiErr.message).toBe('Unexpected failure');
      expect(apiErr.details).toEqual({ correlation_id: 'abc' });
    }
  });

  it('returns parsed JSON on success', async () => {
    const types = await getDocumentTypes();
    expect(types.length).toBeGreaterThan(0);
    expect(types[0].category).toBe('academic_certificate');
  });

  it('returns a verification result from POST /documents/{id}/verify', async () => {
    const result = await startVerification(STUB_DOCUMENT_ID);
    expect(result.verification_id).toBe(STUB_VERIFICATION_ID);
    expect(result.status).toBe('VERIFIED_MATCH');
  });

  it('returns a blockchain record from GET /verifications/{id}/blockchain', async () => {
    const record = await getBlockchain(STUB_VERIFICATION_ID);
    expect(record.recording_status).toBe('CONFIRMED');
    expect(record.transaction_hash).toMatch(/^0x/);
  });

  it('supports chain mode flags through the mock config', async () => {
    setMockConfig({ chain: 'FAILED:RPC_UNAVAILABLE' });
    const record = await getBlockchain(STUB_VERIFICATION_ID);
    expect(record.recording_status).toBe('FAILED');
    expect(record.error_code).toBe('RPC_UNAVAILABLE');
    expect(record.transaction_hash).toBeNull();
  });
});