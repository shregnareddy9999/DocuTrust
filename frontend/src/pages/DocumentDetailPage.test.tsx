import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { DocumentDetailPage } from './DocumentDetailPage';
import { renderWithRouter } from '../test/render';
import { server } from '../test/setup';
import { setMockConfig } from '../mocks/config';
import { STUB_DOCUMENT_ID } from '../mocks/handlers';

const ROUTE = `/documents/${STUB_DOCUMENT_ID}`;
const PATH = '/documents/:documentId';

describe('DocumentDetailPage', () => {
  it('renders extracted fields with confidence and nulls as "Not found"', async () => {
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Aarav Demo')).toBeInTheDocument();
    expect(screen.getByText('DEMO-STU-001')).toBeInTheDocument();
    expect(screen.getAllByText('Read clearly').length).toBeGreaterThan(0);
    expect(screen.getByText('OCR confidence: 94%')).toBeInTheDocument();
    expect(screen.getByText('Not found')).toBeInTheDocument();
  });

  it('shows the low-confidence message for fields below 0.70', async () => {
    server.use(
      http.get(`*/api/v1/documents/${STUB_DOCUMENT_ID}/extraction`, () =>
        HttpResponse.json({
          document_id: STUB_DOCUMENT_ID,
          engine_name: 'demo',
          engine_version: '1',
          status: 'SUCCEEDED',
          warnings: ['low_confidence:student_id'],
          extracted_fields: {
            student_id: { value: 'DEMO-STU-001', confidence: 0.61, source: 'ocr' },
          },
        })
      )
    );
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(
      await screen.findByText('Low confidence — OCR was unsure, may need human review')
    ).toBeInTheDocument();
    expect(screen.getByText('OCR confidence: 61%')).toBeInTheDocument();
  });

  it('shows the synthetic data banner and preview state', async () => {
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Aarav Demo');
    expect(screen.getByText('SYNTHETIC DEMO DATA')).toBeInTheDocument();
    expect(screen.getByText('Preview not available')).toBeInTheDocument();
  });

  it('shows a progress indicator while the comparison runs', async () => {
    setMockConfig({ slow: true });
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Aarav Demo');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Run comparison' }));
    expect(await screen.findByText('Reading and comparing')).toBeInTheDocument();
  });

  it('translates warnings into plain language', async () => {
    setMockConfig({ mock: 'REVIEW_REQUIRED' });
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Semester or Year was read with low confidence')).toBeInTheDocument();
  });

  it('shows a failed extraction instead of a blank screen', async () => {
    setMockConfig({ mock: 'PROCESSING_FAILED' });
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Text extraction could not be completed')).toBeInTheDocument();
  });

  it('shows an error state with retry when the network fails', async () => {
    server.use(http.get(`*/api/v1/documents/${STUB_DOCUMENT_ID}/extraction`, () => HttpResponse.error()));
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('shows an empty state when no extraction is available', async () => {
    server.use(http.get(`*/api/v1/documents/${STUB_DOCUMENT_ID}/extraction`, () => new HttpResponse(null, { status: 204 })));
    renderWithRouter(<DocumentDetailPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('No extraction available')).toBeInTheDocument();
  });
});