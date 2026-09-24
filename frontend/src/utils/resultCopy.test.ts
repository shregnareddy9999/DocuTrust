import { describe, expect, it } from 'vitest';
import { STATUS_EXPLANATIONS } from './resultCopy';
import type { VerificationStatus } from '../types/api';

const statuses: VerificationStatus[] = [
  'PENDING',
  'VERIFIED_MATCH',
  'REVIEW_REQUIRED',
  'NO_TRUSTED_RECORD',
  'INTEGRITY_MISMATCH',
  'PROCESSING_FAILED',
];

describe('STATUS_EXPLANATIONS', () => {
  it('covers every verification status exactly once', () => {
    expect(Object.keys(STATUS_EXPLANATIONS).sort()).toEqual([...statuses].sort());
  });

  it('gives every status a non-empty explanation', () => {
    for (const status of statuses) {
      expect(STATUS_EXPLANATIONS[status].length).toBeGreaterThan(0);
    }
  });
});