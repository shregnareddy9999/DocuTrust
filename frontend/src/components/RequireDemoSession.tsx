import { useCallback, useState, type ReactNode } from 'react';
import { Navigate, Outlet, useNavigate } from 'react-router-dom';
import { SplashPage } from '../pages/SplashPage';
import { getDemoSession, hasSplashBeenShown, markSplashShown } from '../state/demoAuth';

export function RequireDemoSession() {
  const navigate = useNavigate();
  const [splashDone, setSplashDone] = useState(hasSplashBeenShown);

  const handleSplashFinished = useCallback(() => {
    markSplashShown();
    setSplashDone(true);
    navigate('/login', { replace: true });
  }, [navigate]);

  if (!splashDone) {
    return <SplashPage onFinished={handleSplashFinished} />;
  }

  if (!getDemoSession()) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const [splashDone, setSplashDone] = useState(hasSplashBeenShown);

  const handleSplashFinished = useCallback(() => {
    markSplashShown();
    setSplashDone(true);
  }, []);

  if (!splashDone) {
    return <SplashPage onFinished={handleSplashFinished} />;
  }

  if (getDemoSession()) {
    return <Navigate to="/" replace />;
  }

  return children;
}
