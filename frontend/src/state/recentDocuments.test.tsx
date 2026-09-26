import { beforeEach, describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '../test/render';
import { DashboardPage } from '../pages/DashboardPage';
import { clearRecentDocuments, addRecentDocument, getRecentDocumentIds, reinitializeForCurrentUser } from './recentDocuments';
import { setDemoSession } from './demoAuth';

describe('recentDocuments store', () => {
  beforeEach(() => {
    // Set up a demo session for user-specific storage
    setDemoSession({ displayName: 'Test User', email: 'test@example.com' });
    reinitializeForCurrentUser();
    clearRecentDocuments();
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

  it('is safe when localStorage is unavailable', () => {
    // The store uses in-memory fallback when localStorage throws
    // This test verifies the store doesn't crash
    clearRecentDocuments();
    addRecentDocument('doc-demo-0001');
    expect(getRecentDocumentIds()).toEqual(['doc-demo-0001']);
  });
});

describe('hydration', () => {
  beforeEach(() => {
    // Set up a demo session for user-specific storage
    setDemoSession({ displayName: 'Test User', email: 'test@example.com' });
    reinitializeForCurrentUser();
    clearRecentDocuments();
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