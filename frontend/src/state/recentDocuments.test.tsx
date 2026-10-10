import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '../test/render';
import { DashboardPage } from '../pages/DashboardPage';
import { clearRecentDocuments, addRecentDocument, getRecentDocumentIds, reinitializeForCurrentUser } from './recentDocuments';
import { setDemoSession } from './demoAuth';

function installLocalStorageMock(): Map<string, string> {
  const store = new Map<string, string>();
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  });
  return store;
}

describe('recentDocuments store', () => {
  beforeEach(() => {
    installLocalStorageMock();
    // Set up a demo session for user-specific storage
    setDemoSession({ displayName: 'Test User', email: 'test@example.com' });
    reinitializeForCurrentUser();
    clearRecentDocuments();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts empty', () => {
    expect(getRecentDocumentIds()).toEqual([]);
  });

  it('adds a document to the front, deduplicating and capping', () => {
    addRecentDocument('doc-b');
    addRecentDocument('doc-a');
    addRecentDocument('doc-b');
    expect(getRecentDocumentIds()).toEqual(['doc-b', 'doc-a']);
  });

  it('clears the in-memory list when switching to an account with no documents', () => {
    addRecentDocument('doc-a');
    expect(getRecentDocumentIds()).toEqual(['doc-a']);

    setDemoSession({ displayName: 'Empty User', email: 'empty@example.com' });
    reinitializeForCurrentUser();

    expect(getRecentDocumentIds()).toEqual([]);
  });

  it('is safe when localStorage is unavailable', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('storage unavailable');
      },
      setItem: () => {
        throw new Error('storage unavailable');
      },
    });
    // The store uses in-memory fallback when localStorage throws
    // This test verifies the store doesn't crash
    clearRecentDocuments();
    addRecentDocument('doc-demo-0001');
    expect(getRecentDocumentIds()).toEqual(['doc-demo-0001']);
  });
});

describe('hydration', () => {
  beforeEach(() => {
    installLocalStorageMock();
    // Set up a demo session for user-specific storage
    setDemoSession({ displayName: 'Test User', email: 'test@example.com' });
    reinitializeForCurrentUser();
    clearRecentDocuments();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('hydrates a recent document with its current verification via existing endpoints', async () => {
    addRecentDocument('doc-demo-0001');
    renderWithRouter(<DashboardPage />, { route: '/', path: '/' });
    expect(await screen.findByText('marksheet-demo.pdf')).toBeInTheDocument();
    expect(screen.getByText('Academic Certificate')).toBeInTheDocument();
    expect(screen.getByText('Matched our synthetic demo reference')).toBeInTheDocument();
  });

  it('shows an empty state with a verify CTA when nothing has been opened', async () => {
    renderWithRouter(<DashboardPage />, { route: '/', path: '/' });
    expect(await screen.findByText('No documents uploaded, please upload')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Verify a document' })).toBeInTheDocument();
  });
});
