import { useEffect, useRef } from 'react';

interface SplashPageProps {
  onFinished: () => void;
}

export function SplashPage({ onFinished }: SplashPageProps) {
  const onFinishedRef = useRef(onFinished);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- updating ref with latest callback is intentional
  onFinishedRef.current = onFinished;

  useEffect(() => {
    console.log('[SplashPage] Mounted, starting simple timer');
    let finishedCurrent = false;
    
    const finish = () => {
      if (finishedCurrent) return;
      finishedCurrent = true;
      console.log('[SplashPage] Finishing splash immediately');
      onFinishedRef.current();
    };

    const timer = setTimeout(() => {
      console.log('[SplashPage] Timer complete, finishing');
      finish();
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="splash" role="img" aria-label="DocuTrust">
      <div className="splash__inner">
        <img src="/logo.svg" alt="DocuTrust" className="splash__logo" />
        <p className="splash__name">DocuTrust</p>
        <p className="splash__tagline">Synthetic demonstration · document comparison</p>
      </div>
    </div>
  );
}
