import { beforeEach, describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '../test/render';
import { DashboardPage } from '../pages/DashboardPage';
import { clearRecentDocuments, addRecentDocument, getRecentDocumentIds } from './recentDocuments';

describe('recentDocuments store', () => {
  beforeEach(() => {
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
    const originalGetItem = window.localStorage.getItem;
    const originalSetItem = window.localStorage.setItem;
    window.localStorage.getItem = (() => {
      throw new Error('quota');
    }) as typeof window.localStorage.getItem;
    window.localStorage.setItem = (() => {
      throw new Error('quota');
    }) as typeof window.localStorage.setItem;
    try {
      clearRecentDocuments();
      addRecentDocument('doc-demo-0001');
      expect(getRecentDocumentIds()).toEqual(['doc-demo-0001']);
    } finally {
      window.localStorage.getItem = originalGetItem;
      window.localStorage.setItem = originalSetItem;
    }
  });
});

describe('hydration', () => {
  beforeEach(() => {
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
    expect(await screen.findByText('No documents yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Verify a document' })).toBeInTheDocument();
  });
});