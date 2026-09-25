import { describe, expect, it } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { UploadPage } from './UploadPage';
import { server } from '../test/setup';
import { setMockConfig } from '../mocks/config';

function renderUploadPage() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/verifications/:verificationId" element={<div>Result placeholder</div>} />
        <Route path="/verifications/:verificationId/review" element={<div>Review placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
}

async function selectFileAndCategory() {
  const user = userEvent.setup();
  await screen.findByText('1. Choose a category');
  await user.click(screen.getByText('Academic Certificate'));
  const file = new File(['demo'], 'marksheet.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
  expect(screen.getByText(/Selected file:/)).toBeInTheDocument();
}

describe('UploadPage', () => {
  it('renders categories from GET /document-types', async () => {
    renderUploadPage();
    expect(await screen.findByText('Academic Certificate')).toBeInTheDocument();
    expect(screen.getByText('Institutional ID')).toBeInTheDocument();
    expect(screen.getByText('Pan Card')).toBeInTheDocument();
    expect(screen.getByText('Government Certificate')).toBeInTheDocument();
  });

  it('renders the form from the API response, not a hardcoded list', async () => {
    server.use(
      http.get('*/api/v1/document-types', () =>
        HttpResponse.json([
          {
            category: 'custom_category',
            label: 'Custom Category From Server',
            fields: [{ name: 'x', label: 'X', type: 'text', required: true, match_field: true }],
          },
        ])
      )
    );
    renderUploadPage();
    expect(await screen.findByText('Custom Category From Server')).toBeInTheDocument();
    expect(screen.queryByText('Academic Certificate')).not.toBeInTheDocument();
  });

  it('uploads, shows each processing step, then navigates to the comparison result', async () => {
    setMockConfig({ slow: true });
    renderUploadPage();
    await selectFileAndCategory();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload and verify' }));
    expect(await screen.findByText('Document uploaded')).toBeInTheDocument();
    expect(await screen.findByText('Reading and comparing')).toBeInTheDocument();
    expect(
      await screen.findByText('Result placeholder', {}, { timeout: 6000 })
    ).toBeInTheDocument();
  });

  it('navigates to review when the comparison needs a human review', async () => {
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderUploadPage();
    await selectFileAndCategory();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload and verify' }));
    expect(await screen.findByText('Review placeholder', {}, { timeout: 6000 })).toBeInTheDocument();
  });

  it.each([
    ['FILE_TOO_LARGE', 'That file is too large. The maximum upload size is 10 MB.'],
    ['UNSUPPORTED_MEDIA_TYPE', 'That file type is not supported. Use a JPEG, PNG, or PDF.'],
    ['EMPTY_OR_CORRUPT_FILE', 'The file appears to be empty or unreadable. Try another file.'],
    ['INVALID_CATEGORY', 'The selected category is not recognised. Choose one of the listed categories.'],
  ])('renders a distinct message for upload error %s', async (err, expected) => {
    setMockConfig({ err });
    renderUploadPage();
    await selectFileAndCategory();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload and verify' }));
    expect(await screen.findByText(expected)).toBeInTheDocument();
  });

  it('renders a network failure as an error state with retry', async () => {
    server.use(http.get('*/api/v1/document-types', () => HttpResponse.error()));
    renderUploadPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Could not reach the server/)).toBeInTheDocument();
    const retry = screen.getByRole('button', { name: 'Try again' });
    expect(retry).toBeInTheDocument();
  });

  it('keeps the upload button disabled until a category and file are chosen', async () => {
    renderUploadPage();
    await screen.findByText('Academic Certificate');
    expect(screen.getByRole('button', { name: 'Upload and verify' })).toBeDisabled();
  });

  it('shows a loading indicator while document categories load', async () => {
    server.use(
      http.get('*/api/v1/document-types', async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json([
          { category: 'c', label: 'Cat', fields: [] },
        ]);
      })
    );
    renderUploadPage();
    expect(await screen.findByText('Loading document categories…')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Cat')).toBeInTheDocument());
  });
});