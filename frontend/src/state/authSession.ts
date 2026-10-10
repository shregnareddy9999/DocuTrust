import { useSyncExternalStore } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '../utils/supabase';
import { getCurrentProfile } from '../utils/auth';

export interface DemoSession {
  displayName: string;
  email: string;
}

const LAST_ROUTE_KEY = 'docutrust.lastRoute';
const SESSION_RESTORE_KEY = 'docutrust.sessionRestoredAfterLogin';

/**
 * Compatibility layer for existing UI components.
 * Real authentication is managed exclusively by Supabase.
 */
let activeSession: DemoSession | null = null;
let initialized = false;
let splashDoneThisLoad = false;
let interactiveSessionThisLoad = hasInteractiveSessionMarker();

const sessionChangeListeners = new Set<() => void>();

function emitSessionChange(): void {
  for (const listener of sessionChangeListeners) {
    try {
      listener();
    } catch {
      // Keep one listener from affecting the others.
    }
  }
}

function hasInteractiveSessionMarker(): boolean {
  try {
    return sessionStorage.getItem(SESSION_RESTORE_KEY) === 'true';
  } catch {
    return false;
  }
}

function setInteractiveSessionMarker(value: boolean): void {
  interactiveSessionThisLoad = value;

  try {
    if (value) {
      sessionStorage.setItem(SESSION_RESTORE_KEY, 'true');
    } else {
      sessionStorage.removeItem(SESSION_RESTORE_KEY);
    }
  } catch {
    // Storage may be unavailable; keep the in-memory flag for this load.
  }
}

export function onSessionChange(listener: () => void): () => void {
  sessionChangeListeners.add(listener);
  return () => {
    sessionChangeListeners.delete(listener);
  };
}

function mapSupabaseSession(session: Session | null): DemoSession | null {
  if (!interactiveSessionThisLoad) {
    return null;
  }

  const user = session?.user;

  if (!user) {
    return null;
  }

  const metadataName = user.user_metadata?.display_name;

  return {
    email: user.email ?? '',
    displayName:
      (typeof metadataName === 'string' && metadataName.trim()) ||
      user.email?.split('@')[0] ||
      'DocuTrust User',
  };
}

async function refreshProfileFromSupabase(): Promise<void> {
  if (!activeSession) return;

  try {
    const profile = await getCurrentProfile();
    if (!profile) return;

    activeSession = {
      displayName: profile.displayName,
      email: profile.email,
    };
    emitSessionChange();
  } catch {
    // Keep the auth metadata fallback if profile RLS/network access is unavailable.
  }
}

function applySession(session: Session | null): void {
  activeSession = mapSupabaseSession(session);
  initialized = true;
  emitSessionChange();

  if (session) {
    queueMicrotask(() => {
      void refreshProfileFromSupabase();
    });
  }
}

async function loadSupabaseSession(): Promise<void> {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    initialized = true;
    emitSessionChange();
    throw error;
  }

  applySession(data.session);
}

let initializationPromise: Promise<void> | null = null;

export function initializeAuthSession(): Promise<void> {
  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = loadSupabaseSession();

  return initializationPromise;
}

export function refreshAuthSession(): Promise<void> {
  setInteractiveSessionMarker(true);
  return loadSupabaseSession();
}

supabase.auth.onAuthStateChange((_event, session) => {
  applySession(session);
});

export function getDemoSession(): DemoSession | null {
  return activeSession;
}

export function isAuthInitialized(): boolean {
  return initialized;
}

export function useAuthSession(): {
  session: DemoSession | null;
  loading: boolean;
} {
  const session = useSyncExternalStore(
    onSessionChange,
    getDemoSession,
    () => null,
  );

  const ready = useSyncExternalStore(
    onSessionChange,
    isAuthInitialized,
    () => false,
  );

  return { session, loading: !ready };
}

export function hasSplashBeenShown(): boolean {
  return splashDoneThisLoad;
}

export function markSplashShown(): void {
  splashDoneThisLoad = true;
}

export function getLastRoute(): string | null {
  try {
    return sessionStorage.getItem(LAST_ROUTE_KEY);
  } catch {
    return null;
  }
}

export function setLastRoute(route: string): void {
  try {
    sessionStorage.setItem(LAST_ROUTE_KEY, route);
  } catch {
    // Storage may be unavailable.
  }
}

export function sessionInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? 'D';
  const second = parts[1]?.[0] ?? '';

  return `${first}${second}`.toUpperCase();
}

/**
 * Demo-only session injection retained for existing unit tests.
 * Production login must use Supabase.
 */
export function setDemoSession(session: DemoSession): void {
  if (import.meta.env.MODE !== 'test') {
    throw new Error('Demo sessions can only be created in tests.');
  }

  activeSession = session;
  initialized = true;
  emitSessionChange();
}

export function clearDemoSession(): void {
  activeSession = null;
  setInteractiveSessionMarker(false);

  try {
    sessionStorage.removeItem(LAST_ROUTE_KEY);
  } catch {
    // Storage may be unavailable.
  }

  emitSessionChange();
}
