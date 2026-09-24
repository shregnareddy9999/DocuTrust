import { apiRequest } from './client';
import type {
  VerificationResponse,
  VerificationHistoryResponse,
  ReviewRequest,
  ReviewResponse,
  BlockchainResponse,
} from '../types/api';

export async function startVerification(documentId: string): Promise<VerificationResponse> {
  return apiRequest<VerificationResponse>(`/documents/${documentId}/verify`, {
    method: 'POST',
  });
}

export async function getVerification(verificationId: string): Promise<VerificationResponse> {
  return apiRequest<VerificationResponse>(`/verifications/${verificationId}`);
}

export async function getVerificationHistory(
  documentId: string
): Promise<VerificationHistoryResponse> {
  return apiRequest<VerificationHistoryResponse>(`/documents/${documentId}/verifications`);
}

export async function submitReview(
  verificationId: string,
  review: ReviewRequest
): Promise<ReviewResponse> {
  return apiRequest<ReviewResponse>(`/verifications/${verificationId}/review`, {
    method: 'POST',
    body: JSON.stringify(review),
  });
}

export async function getBlockchain(
  verificationId: string
): Promise<BlockchainResponse> {
  return apiRequest<BlockchainResponse>(`/verifications/${verificationId}/blockchain`);
}