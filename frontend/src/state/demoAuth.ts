export interface DemoSession {
  displayName: string;
  email: string;
}

const SPLASH_KEY = 'docutrust.splashDone';
const SESSION_KEY = 'docutrust.demoSession';
const LAST_ROUTE_KEY = 'docutrust.lastRoute';

export function hasSplashBeenShown(): boolean {
  // Always return false so splash shows on every page load/reload
  return false;
}

export function markSplashShown(): void {
  // No-op - we don't persist splash state anymore
}

export function getDemoSession(): DemoSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      parsed &&
      typeof parsed === 'object' &&
      typeof (parsed as DemoSession).displayName === 'string' &&
      typeof (parsed as DemoSession).email === 'string'
    ) {
      return parsed as DemoSession;
    }
    return null;
  } catch {
    return null;
  }
}

export function setDemoSession(session: DemoSession): void {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // localStorage unavailable; the current tab can still proceed via memory if needed
  }
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
    // sessionStorage unavailable
  }
}

export function sessionInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? 'D';
  const second = parts[1]?.[0] ?? '';
  return `${first}${second}`.toUpperCase();
}

export function clearDemoSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(SPLASH_KEY);
    sessionStorage.removeItem(LAST_ROUTE_KEY);
  } catch {
    // storage unavailable
  }
}
