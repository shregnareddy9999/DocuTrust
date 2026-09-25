import { apiRequest } from './client';
import type { DocumentType } from '../types/api';

export async function getDocumentTypes(): Promise<DocumentType[]> {
  return apiRequest<DocumentType[]>('/document-types');
}