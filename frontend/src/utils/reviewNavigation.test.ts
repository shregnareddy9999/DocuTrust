import { describe, expect, it } from 'vitest';
import { needsHumanReview, pathAfterVerification } from './reviewNavigation';

describe('reviewNavigation', () => {
  it('sends only documented review statuses to the review page', () => {
    expect(needsHumanReview('REVIEW_REQUIRED')).toBe(true);
    expect(needsHumanReview('INTEGRITY_MISMATCH')).toBe(true);
    expect(needsHumanReview('VERIFIED_MATCH')).toBe(false);
    expect(needsHumanReview('NO_TRUSTED_RECORD')).toBe(false);
    expect(pathAfterVerification('ver-1', 'REVIEW_REQUIRED')).toBe('/verifications/ver-1/review');
    expect(pathAfterVerification('ver-1', 'VERIFIED_MATCH')).toBe('/verifications/ver-1');
  });
});
