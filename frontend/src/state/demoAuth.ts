export interface DemoSession {
  displayName: string;
  email: string;
}

const REGISTERED_USERS_KEY = 'docutrust.registeredUsers';
const LAST_ROUTE_KEY = 'docutrust.lastRoute';
const STORAGE_KEY_PREFIX = 'docutrust.recentDocuments';
const SESSION_KEY = 'docutrust.demoSession';

function readSessionFromStorage(): DemoSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === 'object' && 'displayName' in parsed && 'email' in parsed) {
      return parsed as DemoSession;
    }
    return null;
  } catch {
    return null;
  }
}

function writeSessionToStorage(session: DemoSession | null): void {
  try {
    if (session) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      sessionStorage.removeItem(SESSION_KEY);
    }
  } catch {
    // storage unavailable
  }
}

/** Active demo session, restored from sessionStorage on load. */
let activeSession: DemoSession | null = readSessionFromStorage();
/** Splash completed during this page load only. */
let splashDoneThisLoad = false;

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
  return splashDoneThisLoad;
}

export function markSplashShown(): void {
  splashDoneThisLoad = true;
}

export function getDemoSession(): DemoSession | null {
  return activeSession;
}

export function setDemoSession(session: DemoSession): void {
  activeSession = session;
  writeSessionToStorage(session);
  emitSessionChange();
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
  activeSession = null;
  writeSessionToStorage(null);
  try {
    sessionStorage.removeItem(LAST_ROUTE_KEY);
  } catch {
    // storage unavailable
  }
  emitSessionChange();
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

export function deleteDemoAccount(): void {
  try {
    const session = getDemoSession();
    if (session) {
      const users = readRegisteredUsers();
      const filtered = users.filter((e) => e.toLowerCase() !== session.email.toLowerCase());
      writeRegisteredUsers(filtered);
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}.${session.email.toLowerCase()}`);
    }
    clearDemoSession();
  } catch {
    clearDemoSession();
  }
}
