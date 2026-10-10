export {
  type DemoSession,
  initializeAuthSession,
  refreshAuthSession,
  isAuthInitialized,
  useAuthSession,
  getDemoSession,
  onSessionChange,
  hasSplashBeenShown,
  markSplashShown,
  getLastRoute,
  setLastRoute,
  sessionInitials,
  setDemoSession,
  clearDemoSession,
} from './authSession';

/**
 * Legacy demo-account functions are intentionally disabled.
 * Supabase Auth now manages real user accounts.
 */
export function isEmailRegistered(_email: string): boolean {
  return false;
}

export function registerEmail(_email: string): void {
  throw new Error(
    'Demo registration is disabled. Use Supabase authentication.',
  );
}

export function getRegisteredEmails(): string[] {
  return [];
}

export function deleteDemoAccount(): void {
  throw new Error(
    'Use the Supabase-backed account deletion flow.',
  );
}
