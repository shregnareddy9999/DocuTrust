import { useEffect, useRef, useState } from 'react';

interface SplashPageProps {
  onFinished: () => void;
}

type SplashPhase = 'enter' | 'hold';

export function SplashPage({ onFinished }: SplashPageProps) {
  const finished = useRef(false);
  const [phase, setPhase] = useState<SplashPhase>('enter');

  function finish(): void {
    if (finished.current) return;
    finished.current = true;
    onFinished();
  }

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      finish();
    }
  }, []);

  function handleAnimationEnd(): void {
    if (phase === 'enter') {
      setPhase('hold');
      return;
    }
    finish();
  }

  return (
    <div className="splash" role="img" aria-label="DocuTrust">
      <div
        className={`splash__inner splash__inner--${phase}`}
        onAnimationEnd={handleAnimationEnd}
      >
        <img src="/logo.png" alt="DocuTrust" className="splash__logo" />
        <p className="splash__name"></p>
        <p className="splash__tagline">Synthetic demonstration · document comparison</p>
      </div>
    </div>
  );
}
