import { apiRequest } from './client';

import type {
  AcademicSummaryRequest,
  AcademicSummaryResponse,
} from '../types/api';

export type { AcademicSummaryResponse };

export async function generateAcademicSummary(
  request: AcademicSummaryRequest,
): Promise<AcademicSummaryResponse> {
  return apiRequest<AcademicSummaryResponse>(
    '/academic-summary',
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );
}
