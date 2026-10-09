import { apiBlobRequest, apiRequest } from './client';
import type { UploadResponse, Document, ExtractionResponse } from '../types/api';

export async function uploadDocument(
  file: File,
  category: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);

  return apiRequest<UploadResponse>('/documents', {
    method: 'POST',
    body: formData,
  });
}

export async function getDocument(documentId: string): Promise<Document> {
  return apiRequest<Document>(`/documents/${documentId}`);
}

export async function getExtraction(documentId: string): Promise<ExtractionResponse> {
  return apiRequest<ExtractionResponse>(`/documents/${documentId}/extraction`);
}

export async function getDocumentFile(documentId: string): Promise<Blob> {
  return apiBlobRequest(`/documents/${documentId}/file`);
}

export async function deleteDocument(documentId: string): Promise<void> {
  return apiRequest<void>(`/documents/${documentId}`, {
    method: 'DELETE',
  });
}
