import { supabase } from './supabase';

export interface AuthProfile {
  id: string;
  email: string;
  displayName: string;
}

export async function registerUser(
  displayName: string,
  email: string,
  password: string,
): Promise<{ needsEmailConfirmation: boolean }> {
  const normalizedEmail = email.trim().toLowerCase();
  const normalizedName = displayName.trim();
  const emailRedirectTo =
    typeof window === 'undefined' ? undefined : `${window.location.origin}/login`;

  const { data, error } = await supabase.auth.signUp({
    email: normalizedEmail,
    password,
    options: {
      emailRedirectTo,
      data: {
        display_name: normalizedName,
      },
    },
  });

  if (error) {
    throw error;
  }

  if (!data.user) {
    throw new Error('Registration could not be completed. Please try again.');
  }

  if (data.session && normalizedName) {
    const { error: profileError } = await supabase
      .from('profiles')
      .upsert(
        {
          id: data.user.id,
          display_name: normalizedName,
        },
        { onConflict: 'id' },
      );

    if (profileError) {
      console.warn('Supabase profile could not be saved:', profileError.message);
    }
  }

  return {
    needsEmailConfirmation: !data.session,
  };
}

export async function loginUser(
  email: string,
  password: string,
): Promise<void> {
  const { data, error } = await supabase.auth.signInWithPassword({
    email: email.trim().toLowerCase(),
    password,
  });

  if (error) {
    throw error;
  }

  if (!data.session) {
    throw new Error('Sign in did not return an active session.');
  }
}

export async function logoutUser(): Promise<void> {
  const { error } = await supabase.auth.signOut();

  if (error) {
    throw error;
  }
}

export async function clearSupabaseSession(): Promise<void> {
  await supabase.auth.signOut({ scope: 'local' });
}

export async function getCurrentProfile(): Promise<AuthProfile | null> {
  const { data: authData, error: authError } =
    await supabase.auth.getUser();

  if (authError || !authData.user) {
    return null;
  }

  const user = authData.user;
  const metadataName = user.user_metadata?.display_name;

  const { data: profile, error: profileError } = await supabase
    .from('profiles')
    .select('display_name')
    .eq('id', user.id)
    .maybeSingle();

  if (profileError) {
    throw profileError;
  }

  return {
    id: user.id,
    email: user.email ?? '',
    displayName:
      profile?.display_name ||
      (typeof metadataName === 'string' ? metadataName : '') ||
      user.email?.split('@')[0] ||
      'DocuTrust User',
  };
}
