import { beforeEach, describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '../test/render';
import { clearRecentDocuments, addRecentDocument } from '../state/recentDocuments';
import { resetMockConfig, setMockConfig } from '../mocks/config';
import { DocumentsPage } from './DocumentsPage';
import { ReviewQueuePage } from './ReviewQueuePage';
import { HistoryPage } from './HistoryPage';

const DOC_ID = 'doc-demo-0001';

beforeEach(() => {
  resetMockConfig();
  clearRecentDocuments();
});

describe('DocumentsPage', () => {
  it('lists documents opened in this browser session with their current outcome', async () => {
    addRecentDocument(DOC_ID);
    renderWithRouter(<DocumentsPage />, { route: '/documents', path: '/documents' });
    expect(await screen.findByText('marksheet-demo.pdf')).toBeInTheDocument();
    expect(screen.getByText('Academic Certificate')).toBeInTheDocument();
    expect(screen.getByText('Matched our synthetic demo reference')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open' })).toHaveAttribute('href', `/documents/${DOC_ID}`);
  });

  it('shows the required empty copy', async () => {
    renderWithRouter(<DocumentsPage />, { route: '/documents', path: '/documents' });
    expect(await screen.findByText('No documents yet')).toBeInTheDocument();
  });
});

describe('ReviewQueuePage', () => {
  it('queues only documents whose current outcome needs a human review', async () => {
    addRecentDocument(DOC_ID);
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderWithRouter(<ReviewQueuePage />, { route: '/review-queue', path: '/review-queue' });
    expect(await screen.findByText('marksheet-demo.pdf')).toBeInTheDocument();
    expect(screen.getByText('Mismatch found')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Review' })).toHaveAttribute(
      'href',
      '/verifications/ver-demo-0001/review'
    );
  });

  it('shows the required empty copy when nothing needs review', async () => {
    addRecentDocument(DOC_ID);
    renderWithRouter(<ReviewQueuePage />, { route: '/review-queue', path: '/review-queue' });
    expect(await screen.findByText('No documents need review')).toBeInTheDocument();
  });
});

describe('HistoryPage', () => {
  it('shows verification history with Reviewed by fallback and current marker', async () => {
    addRecentDocument(DOC_ID);
    renderWithRouter(<HistoryPage />, { route: '/history', path: '/history' });
    expect(await screen.findAllByText('marksheet-demo.pdf')).not.toHaveLength(0);
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.getByText('Current result')).toBeInTheDocument();
    expect(screen.getByText('Earlier')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'View' }).length).toBeGreaterThan(0);
  });

  it('shows the required empty copy when there is no history', async () => {
    renderWithRouter(<HistoryPage />, { route: '/history', path: '/history' });
    expect(await screen.findByText('No verification history yet')).toBeInTheDocument();
  });
});