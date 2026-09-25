import { beforeEach, describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { clearRecentDocuments, addRecentDocument } from '../state/recentDocuments';
import { resetMockConfig } from '../mocks/config';
import { DemoDashboardPage } from './DemoDashboardPage';

const DOC_ID = 'doc-demo-0001';

function renderDemo(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/demo" element={<DemoDashboardPage />} />
        <Route path="/demo/:documentId" element={<DemoDashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  resetMockConfig();
  clearRecentDocuments();
});

describe('DemoDashboardPage', () => {
  it('redirects to the most recent document when one exists and projects it', async () => {
    addRecentDocument(DOC_ID);
    renderDemo('/demo');
    expect(await screen.findByText('PS21 Live Demo')).toBeInTheDocument();
    expect(await screen.findByText('marksheet-demo.pdf')).toBeInTheDocument();
    expect(await screen.findByText('Matched our synthetic demo reference')).toBeInTheDocument();
  });

  it('shows an EmptyState with a link to Verify Document when there are no documents', () => {
    renderDemo('/demo');
    expect(screen.getByText('No documents yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Verify a document' })).toHaveAttribute('href', '/verify');
  });
});