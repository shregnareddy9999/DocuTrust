import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initMockConfigFromUrl } from './mocks/config'
import './styles.css'

const search = window.location.search
initMockConfigFromUrl(search)

const hasMockFlags = /[?&](mock|chain|err|net|slow)=/.test(search)

async function bootstrap() {
  if (hasMockFlags) {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}

bootstrap()