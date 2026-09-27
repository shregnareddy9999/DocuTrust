import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initMockConfigFromUrl } from './mocks/config'
import './styles.css'

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

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', textAlign: 'center', fontFamily: 'system-ui' }}>
          <h2>Could not load the application</h2>
          <p>Reload the page and try again.</p>
          <button type="button" onClick={() => window.location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}

async function bootstrap() {
  if (hasMockFlags) {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  )
}

bootstrap()
