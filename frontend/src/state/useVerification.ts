import { useState, useCallback } from 'react';
import {
  startVerification,
  getVerification,
  getVerificationHistory,
  submitReview,
  getBlockchain,
} from '../api/verifications';
import type {
  VerificationResponse,
  VerificationHistoryResponse,
  ReviewRequest,
  ReviewResponse,
  BlockchainResponse,
} from '../types/api';
import type { ApiError } from '../api/client';
import { toApiError } from '../utils/messages';

interface UseVerificationState {
  verification: VerificationResponse | null;
  history: VerificationHistoryResponse | null;
  blockchain: BlockchainResponse | null;
  loading: boolean;
  error: ApiError | null;
  reviewSubmitting: boolean;
}

interface UseVerificationActions {
  runVerification: (documentId: string) => Promise<VerificationResponse>;
  fetchVerification: (verificationId: string) => Promise<void>;
  fetchHistory: (documentId: string) => Promise<void>;
  fetchBlockchain: (verificationId: string) => Promise<void>;
  submitReview: (verificationId: string, review: ReviewRequest) => Promise<ReviewResponse>;
  clearError: () => void;
  reset: () => void;
}

export function useVerification(): UseVerificationState & UseVerificationActions {
  const [state, setState] = useState<UseVerificationState>({
    verification: null,
    history: null,
    blockchain: null,
    loading: false,
    error: null,
    reviewSubmitting: false,
  });

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  const reset = useCallback(() => {
    setState({
      verification: null,
      history: null,
      blockchain: null,
      loading: false,
      error: null,
      reviewSubmitting: false,
    });
  }, []);

  const runVerification = useCallback(async (documentId: string): Promise<VerificationResponse> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const verification = await startVerification(documentId);
      setState((prev) => ({ ...prev, verification, loading: false }));
      return verification;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Verification failed'),
      }));
      throw error;
    }
  }, []);

  const fetchVerification = useCallback(async (verificationId: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const verification = await getVerification(verificationId);
      setState((prev) => ({ ...prev, verification, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch verification'),
      }));
    }
  }, []);

  const fetchHistory = useCallback(async (documentId: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const history = await getVerificationHistory(documentId);
      setState((prev) => ({ ...prev, history, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch history'),
      }));
    }
  }, []);

  const fetchBlockchain = useCallback(async (verificationId: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const blockchain = await getBlockchain(verificationId);
      setState((prev) => ({ ...prev, blockchain, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch blockchain status'),
      }));
    }
  }, []);

  const submitReviewAction = useCallback(
    async (verificationId: string, review: ReviewRequest): Promise<ReviewResponse> => {
      setState((prev) => ({ ...prev, reviewSubmitting: true, error: null }));
      try {
        const response = await submitReview(verificationId, review);
        setState((prev) => ({ ...prev, reviewSubmitting: false }));
        return response;
      } catch (error) {
        setState((prev) => ({
          ...prev,
          reviewSubmitting: false,
          error: toApiError(error, 'Review submission failed'),
        }));
        throw error;
      }
    },
    []
  );

  return {
    ...state,
    runVerification,
    fetchVerification,
    fetchHistory,
    fetchBlockchain,
    submitReview: submitReviewAction,
    clearError,
    reset,
  };
}