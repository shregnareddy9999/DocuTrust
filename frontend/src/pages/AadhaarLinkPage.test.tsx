import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { AadhaarLinkPage } from './AadhaarLinkPage';
import { server } from '../test/setup';
import { setMockConfig } from '../mocks/config';

function renderPage() {
  return render(<AadhaarLinkPage />);
}

async function chooseFile(name = 'aadhaar_AAD-10001.png', type = 'image/png') {
  const file = new File(['demo aadhaar'], name, { type });
  fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
  expect(screen.getByText(/Selected file:/)).toBeInTheDocument();
}

describe('AadhaarLinkPage', () => {
  it('uploads a synthetic Aadhaar demo file and renders linked records', async () => {
    renderPage();
    await chooseFile();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload & Find Links' }));

    expect(await screen.findByText('Aarav Demo')).toBeInTheDocument();
    expect(screen.getByText('CIT-10001 linked through AAD-10001')).toBeInTheDocument();
    expect(screen.getByText('3 Records')).toBeInTheDocument();
    expect(screen.getByText('Permanent Account Number Demo')).toBeInTheDocument();
    expect(screen.getByText('Driving Licence Demo')).toBeInTheDocument();
    expect(screen.getByText(/synthetic demo mobile: 9000005001/)).toBeInTheDocument();
    expect(screen.getByText('No sample document')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mobile Connection Demo/ })).not.toBeInTheDocument();
  });

  it('opens image and PDF sample previews from clickable rows', async () => {
    renderPage();
    await chooseFile();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload & Find Links' }));

    const panRow = await screen.findByRole('button', { name: /Permanent Account Number Demo/ });
    await userEvent.setup().click(panRow);
    expect(await screen.findByRole('img', { name: /Permanent Account Number Demo synthetic sample/ })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Close preview' }));

    const dlRow = screen.getByRole('button', { name: /Driving Licence Demo/ });
    await userEvent.setup().click(dlRow);
    expect(await screen.findByTitle('Driving Licence Demo')).toBeInTheDocument();
  });

  it('shows a clear message when a non-Aadhaar demo document is uploaded', async () => {
    setMockConfig({ err: 'AADHAAR_DEMO_CARD_REQUIRED' });
    renderPage();
    await chooseFile('pan-like-demo.png', 'image/png');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload & Find Links' }));

    expect(
      await screen.findByText('Upload a DocuTrust synthetic Aadhaar demo card. Other document types are not accepted on this page.')
    ).toBeInTheDocument();
  });

  it('renders a loading state while the lookup is running', async () => {
    setMockConfig({ slow: true });
    renderPage();
    await chooseFile();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload & Find Links' }));

    expect(await screen.findByText('Reading the synthetic demo link...')).toBeInTheDocument();
    expect(await screen.findByText('Aarav Demo')).toBeInTheDocument();
  });

  it('handles a row with a missing local sample asset', async () => {
    server.use(
      http.post('*/api/v1/aadhaar-link', () =>
        HttpResponse.json({
          lookup_id: 'aadhaar-link-demo-missing',
          source: 'synthetic-demo',
          reference_detected: true,
          citizen: {
            citizen_ref: 'CIT-10002',
            demo_name: 'Meera Demo',
            aadhaar_ref: 'AAD-10002',
            masked_aadhaar: 'DEMO-XXXX-0002',
            demo_mobile_placeholder: '9000005002',
          },
          linked_documents: [
            {
              id: 'missing-asset',
              document_type: 'BANK_ACCOUNT',
              document_type_label: 'Bank Account Demo',
              demo_document_ref: 'BNK-60002',
              display_value: 'Bank Account reference: BNK-60002',
              issuer_label: 'Synthetic Banking Registry',
              asset_ref: null,
              asset_mime_type: null,
              status_label: 'Listed in synthetic registry',
              demo_mobile_placeholder: null,
            },
          ],
          summary: {
            linked_record_count: 1,
            blockchain_seed: 'local-demo-seed',
            last_sync_label: 'Synthetic demo registry snapshot',
          },
        })
      )
    );

    renderPage();
    await chooseFile('aadhaar_AAD-10002.pdf', 'application/pdf');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Upload & Find Links' }));
    expect(await screen.findByText('Bank Account Demo')).toBeInTheDocument();
    expect(screen.getByText('No sample document')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
