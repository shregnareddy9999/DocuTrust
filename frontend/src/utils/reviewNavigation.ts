import type { VerificationStatus } from '../types/api';

/** Review is only for these two statuses (tasks/11-frontend.md, docs/frontend.md). */
export function needsHumanReview(status: VerificationStatus): boolean {
  return status === 'REVIEW_REQUIRED' || status === 'INTEGRITY_MISMATCH';
}

export function pathAfterVerification(verificationId: string, status: VerificationStatus): string {
  if (needsHumanReview(status)) {
    return `/verifications/${verificationId}/review`;
  }
  return `/verifications/${verificationId}`;
}
