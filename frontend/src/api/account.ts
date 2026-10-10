import { apiRequest } from './client';
import { supabase } from '../utils/supabase';

export async function deleteCurrentAccount(): Promise<void> {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    throw error;
  }

  const accessToken = data.session?.access_token;
  if (!accessToken) {
    throw new Error('Sign in before deleting the account.');
  }

  await apiRequest<void>('/account', {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
