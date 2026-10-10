import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { SplashPage } from '../pages/SplashPage';
import {
  hasSplashBeenShown,
  initializeAuthSession,
  isAuthInitialized,
  markSplashShown,
  useAuthSession,
} from '../state/authSession';

function useRestoreAuthSession(): string | null {
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthInitialized()) return;

    void initializeAuthSession().catch(() => {
      setAuthError('Unable to restore your session. Please refresh and try again.');
    });
  }, []);

  return authError;
}

export function RequireDemoSession() {
  const { session, loading } = useAuthSession();
  const [splashDone, setSplashDone] = useState(hasSplashBeenShown);
  const authError = useRestoreAuthSession();

  const handleSplashFinished = useCallback(() => {
    markSplashShown();
    setSplashDone(true);
  }, []);

  if (!splashDone) {
    return <SplashPage onFinished={handleSplashFinished} />;
  }

  if (authError) {
    return (
      <div className="page">
        <h1>Session unavailable</h1>
        <p role="alert">{authError}</p>
        <button
          type="button"
          className="button button--primary"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  if (loading) {
    return <div className="page" role="status">Restoring your session...</div>;
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { session, loading } = useAuthSession();
  const [splashDone, setSplashDone] = useState(hasSplashBeenShown);
  const authError = useRestoreAuthSession();

  const handleSplashFinished = useCallback(() => {
    markSplashShown();
    setSplashDone(true);
  }, []);

  if (!splashDone) {
    return <SplashPage onFinished={handleSplashFinished} />;
  }

  if (authError) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <p className="error-inline" role="alert">{authError}</p>
          <button
            type="button"
            className="button button--primary"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="auth-screen" role="status">Restoring your session...</div>;
  }

  if (session) {
    return <Navigate to="/" replace />;
  }

  return children;
}
