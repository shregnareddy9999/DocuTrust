import { useState, useCallback } from 'react';
import { uploadDocument, getDocument, getExtraction } from '../api/documents';
import { getDocumentTypes } from '../api/documentTypes';
import type { Document, ExtractionResponse, DocumentType, UploadResponse } from '../types/api';
import type { ApiError } from '../api/client';
import { toApiError } from '../utils/messages';

interface UseDocumentState {
  document: Document | null;
  extraction: ExtractionResponse | null;
  documentTypes: DocumentType[];
  loading: boolean;
  error: ApiError | null;
  uploadProgress: number;
}

interface UseDocumentActions {
  fetchDocumentTypes: () => Promise<void>;
  upload: (file: File, category: string) => Promise<UploadResponse>;
  fetchDocument: (documentId: string) => Promise<void>;
  fetchExtraction: (documentId: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export function useDocument(): UseDocumentState & UseDocumentActions {
  const [state, setState] = useState<UseDocumentState>({
    document: null,
    extraction: null,
    documentTypes: [],
    loading: false,
    error: null,
    uploadProgress: 0,
  });

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  const reset = useCallback(() => {
    setState({
      document: null,
      extraction: null,
      documentTypes: [],
      loading: false,
      error: null,
      uploadProgress: 0,
    });
  }, []);

  const fetchDocumentTypes = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const types = await getDocumentTypes();
      setState((prev) => ({ ...prev, documentTypes: types, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch document types'),
      }));
    }
  }, []);

  const upload = useCallback(async (file: File, category: string): Promise<UploadResponse> => {
    setState((prev) => ({ ...prev, loading: true, error: null, uploadProgress: 0 }));

    try {
      const response = await uploadDocument(file, category);
      setState((prev) => ({ ...prev, loading: false, uploadProgress: 100 }));
      return response;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        uploadProgress: 0,
        error: toApiError(error, 'Upload failed'),
      }));
      throw error;
    }
  }, []);

  const fetchDocument = useCallback(async (documentId: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const document = await getDocument(documentId);
      setState((prev) => ({ ...prev, document, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch document'),
      }));
    }
  }, []);

  const fetchExtraction = useCallback(async (documentId: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const extraction = await getExtraction(documentId);
      setState((prev) => ({ ...prev, extraction, loading: false }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: toApiError(error, 'Failed to fetch extraction'),
      }));
    }
  }, []);

  return {
    ...state,
    fetchDocumentTypes,
    upload,
    fetchDocument,
    fetchExtraction,
    clearError,
    reset,
  };
}