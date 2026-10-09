import { apiRequest } from './client';
import type { AcademicSummaryResponse } from '../types/api';

export async function generateAcademicSummary(
  documentIds: string[]
): Promise<AcademicSummaryResponse> {
  return apiRequest<AcademicSummaryResponse>('/academic-summary', {
    method: 'POST',
    body: JSON.stringify({ document_ids: documentIds }),
  });
}
