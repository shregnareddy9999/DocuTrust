import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initMockConfigFromUrl } from './mocks/config'
import './styles.css'

console.log('[main] Starting app bootstrap');

const search = window.location.search
initMockConfigFromUrl(search)

const hasMockFlags = /[?&](mock|chain|err|net|slow)=/.test(search)

function cleanUrlIfNeeded(): void {
  const url = new URL(window.location.href)
  const hasMockParams = /[?&](mock|chain|err|net|slow)=/.test(url.search)
  if (hasMockParams && url.pathname === '/') {
    url.search = ''
    window.history.replaceState({}, '', url.toString())
  }
}

cleanUrlIfNeeded()

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', textAlign: 'center', color: 'red', fontFamily: 'system-ui' }}>
          <h2>Application Error</h2>
          <p>{this.state.error?.message}</p>
          <pre style={{ textAlign: 'left', maxWidth: '600px', margin: '20px auto' }}>{this.state.error?.stack}</pre>
          <button onClick={() => window.location.reload()}>Reload Application</button>
        </div>
      );
    }
    return this.props.children;
  }
}

async function bootstrap() {
  console.log('[main] bootstrap called, hasMockFlags:', hasMockFlags);
  if (hasMockFlags) {
    console.log('[main] Starting MSW worker');
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
    console.log('[main] MSW worker started');
  }

  console.log('[main] Rendering React app');
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  )
  console.log('[main] React app rendered');
}

bootstrap()