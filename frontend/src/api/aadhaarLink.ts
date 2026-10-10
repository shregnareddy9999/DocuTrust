import { apiRequest, getApiBaseUrl } from './client';
import type { AadhaarLinkResponse } from '../types/api';

export async function uploadAadhaarLinkDocument(file: File): Promise<AadhaarLinkResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest<AadhaarLinkResponse>('/aadhaar-link', {
    method: 'POST',
    body: formData,
  });
}

export function getAadhaarAssetUrl(assetRef: string): string {
  return `${getApiBaseUrl()}/aadhaar-link/assets/${encodeURIComponent(assetRef)}`;
}
