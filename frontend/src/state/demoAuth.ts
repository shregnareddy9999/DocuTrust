export interface DemoSession {
  displayName: string;
  email: string;
}

const SPLASH_KEY = 'docutrust.splashDone';
const SESSION_KEY = 'docutrust.demoSession';
const LAST_ROUTE_KEY = 'docutrust.lastRoute';
const REGISTERED_USERS_KEY = 'docutrust.registeredUsers';

const sessionChangeListeners = new Set<() => void>();

export function onSessionChange(listener: () => void): () => void {
  sessionChangeListeners.add(listener);
  return () => {
    sessionChangeListeners.delete(listener);
  };
}

function emitSessionChange(): void {
  for (const listener of sessionChangeListeners) {
    try {
      listener();
    } catch {
      // ignore listener errors
    }
  }
}

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
    emitSessionChange();
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
    emitSessionChange();
  } catch {
    // storage unavailable
  }
}

function readRegisteredUsers(): string[] {
  try {
    const raw = localStorage.getItem(REGISTERED_USERS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.filter((email): email is string => typeof email === 'string');
    }
    return [];
  } catch {
    return [];
  }
}

function writeRegisteredUsers(users: string[]): void {
  try {
    localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(users));
  } catch {
    // storage unavailable
  }
}

export function isEmailRegistered(email: string): boolean {
  const users = readRegisteredUsers();
  return users.some((e) => e.toLowerCase() === email.toLowerCase());
}

export function registerEmail(email: string): void {
  const users = readRegisteredUsers();
  const normalized = email.toLowerCase();
  if (!users.some((e) => e.toLowerCase() === normalized)) {
    users.push(normalized);
    writeRegisteredUsers(users);
  }
}

export function getRegisteredEmails(): string[] {
  return readRegisteredUsers();
}
