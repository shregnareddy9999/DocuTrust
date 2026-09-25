import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Navigate, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { SplashPage } from '../pages/SplashPage';
import { getDemoSession, hasSplashBeenShown, markSplashShown, getLastRoute, setLastRoute } from '../state/demoAuth';

export function RequireDemoSession() {
  const navigate = useNavigate();
  const location = useLocation();
  const [splashDone, setSplashDone] = useState(hasSplashBeenShown);

  // Store the current route (except auth pages) for restoration after reload
  useEffect(() => {
    const currentPath = location.pathname;
    if (currentPath !== '/login' && currentPath !== '/register') {
      setLastRoute(currentPath);
    }
  }, [location.pathname]);

  const handleSplashFinished = useCallback(() => {
    console.log('[RequireDemoSession] Splash finished, checking demo session');
    markSplashShown();
    setSplashDone(true);
    if (!getDemoSession()) {
      console.log('[RequireDemoSession] No demo session, navigating to login');
      navigate('/login', { replace: true });
    } else {
      const lastRoute = getLastRoute();
      if (lastRoute && lastRoute !== '/login' && lastRoute !== '/register') {
        console.log('[RequireDemoSession] Restoring last route:', lastRoute);
        navigate(lastRoute, { replace: true });
      }
    }
  }, [navigate]);

  if (!splashDone) {
    console.log('[RequireDemoSession] Showing splash page');
    return (
      <SplashPage onFinished={handleSplashFinished} />
    );
  }

  console.log('[RequireDemoSession] Splash done, checking demo session');
  if (!getDemoSession()) {
    console.log('[RequireDemoSession] No demo session, navigating to login');
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
    return (
      <SplashPage onFinished={handleSplashFinished} />
    );
  }

  if (getDemoSession()) {
    return <Navigate to="/" replace />;
  }

  return children;
}
