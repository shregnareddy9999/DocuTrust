import { apiRequest, getApiBaseUrl } from './client';
import { supabase } from '../utils/supabase';
import type { AadhaarLinkResponse, AadhaarMessageResponse } from '../types/api';

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

export async function sendAadhaarReminderMessage(
  citizenRef: string,
  message: string,
  idempotencyKey: string
): Promise<AadhaarMessageResponse> {
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw error;
  }

  const accessToken = data.session?.access_token;
  if (!accessToken) {
    throw new Error('Sign in before sending a reminder.');
  }

  return apiRequest<AadhaarMessageResponse>(
    `/aadhaar-link/${encodeURIComponent(citizenRef)}/message`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        message,
        idempotency_key: idempotencyKey,
      }),
    }
  );
}
