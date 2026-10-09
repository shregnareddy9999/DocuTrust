import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, waitFor } from '@testing-library/react';
import { http, HttpResponse, delay } from 'msw';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '../test/render';
import { resetMockConfig, setMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';
import { server } from '../test/setup';
import { AcademicSummaryPage } from './AcademicSummaryPage';

beforeEach(() => {
  resetMockConfig();
  resetMockCounters();
});

function uploadFiles(files: File[]): void {
  fireEvent.change(screen.getByTestId('summary-file-input'), {
    target: { files },
  });
}

describe('AcademicSummaryPage', () => {
  it('uploads multiple academic documents and summarizes all uploaded documents', async () => {
    const user = userEvent.setup();
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([
      new File([new Uint8Array([1, 2, 3])], 'semester-1.png', { type: 'image/png' }),
      new File([new Uint8Array([4, 5, 6])], 'semester-2.png', { type: 'image/png' }),
    ]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));

    expect(await screen.findAllByText('marksheet-demo.pdf')).toHaveLength(2);

    await user.click(screen.getByRole('button', { name: 'Generate AI Summary' }));

    expect(await screen.findByText('Documents Analyzed')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText(/Aarav Demo submitted synthetic academic documents/)).toBeInTheDocument();
  });

  it('summarizes one uploaded document', async () => {
    const user = userEvent.setup();
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await screen.findByText('marksheet-demo.pdf');
    await user.click(screen.getByRole('button', { name: 'Generate AI Summary' }));

    expect(await screen.findByText('Documents Analyzed')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows a useful Ollama error', async () => {
    const user = userEvent.setup();
    setMockConfig({ err: 'AI_SUMMARY_UNAVAILABLE' });
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await screen.findByText('marksheet-demo.pdf');
    await user.click(screen.getByRole('button', { name: 'Generate AI Summary' }));

    expect(await screen.findByText(/Could not reach local Ollama/)).toBeInTheDocument();
  });

  it('prevents duplicate summary requests for the same click burst', async () => {
    const user = userEvent.setup();
    let requests = 0;
    server.use(
      http.post('*/api/v1/academic-summary', async () => {
        requests += 1;
        await delay(100);
        return HttpResponse.json({
          summary: 'One summary request was accepted.',
          documents_analyzed: 1,
          model: 'llama3.2:latest',
        });
      })
    );
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await screen.findByText('marksheet-demo.pdf');
    const button = screen.getByRole('button', { name: 'Generate AI Summary' });
    await Promise.all([user.click(button), user.click(button)]);

    expect(await screen.findByText('One summary request was accepted.')).toBeInTheDocument();
    expect(requests).toBe(1);
  });

  it('opens an uploaded document preview', async () => {
    const user = userEvent.setup();
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await user.click(await screen.findByRole('button', { name: 'marksheet-demo.pdf' }));

    expect(await screen.findByLabelText('Document preview')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'marksheet-demo.pdf' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download Document' })).toBeInTheDocument();
  });

  it('deletes an uploaded document after confirmation', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await user.click(await screen.findByRole('button', { name: /Delete marksheet-demo.pdf/i }));

    await waitFor(() => {
      expect(screen.queryByText('marksheet-demo.pdf')).not.toBeInTheDocument();
    });
  });

  it('shows a delete failure without removing the uploaded document', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    setMockConfig({ err: 'DOCUMENT_HAS_HISTORY' });
    renderWithRouter(<AcademicSummaryPage />, {
      route: '/academic-summary',
      path: '/academic-summary',
    });

    uploadFiles([new File([new Uint8Array([1])], 'semester-1.png', { type: 'image/png' })]);
    await user.click(screen.getByRole('button', { name: 'Upload Documents' }));
    await user.click(await screen.findByRole('button', { name: /Delete marksheet-demo.pdf/i }));

    expect(await screen.findByText('Documents with verification history cannot be deleted.')).toBeInTheDocument();
    expect(screen.getByText('marksheet-demo.pdf')).toBeInTheDocument();
  });
});
