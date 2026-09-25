import { describe, expect, it, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { BlockchainReceiptPage } from './BlockchainReceiptPage';
import { renderWithRouter } from '../test/render';
import { server } from '../test/setup';
import { setMockConfig, resetMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';

const TEST_VERIFICATION_ID = 'ver-demo-0001';
const ROUTE = `/verifications/${TEST_VERIFICATION_ID}/blockchain`;
const PATH = '/verifications/:verificationId/blockchain';

describe('BlockchainReceiptPage', () => {
  beforeEach(() => {
    resetMockConfig();
    resetMockCounters();
    server.resetHandlers();
  });

  it('renders a confirmed receipt with hash, chain and timestamps', async () => {
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Verification outcome recorded on-chain')).toBeInTheDocument();
    expect(screen.getByText('Transaction hash')).toBeInTheDocument();
    expect(screen.getByText('Chain ID')).toBeInTheDocument();
    expect(screen.getByText('Contract address')).toBeInTheDocument();
  });

  it('explains what the record proves and what it does not', async () => {
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText(/What this record proves/)).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/not a document hash/i);
  });

  it('renders a FAILED recording in plain language with error_code, without success styling', async () => {
    setMockConfig({ chain: 'FAILED:RPC_UNAVAILABLE' });
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('On-chain recording failed')).toBeInTheDocument();
    expect(screen.getByText(/Could not reach the blockchain network/)).toBeInTheDocument();
    expect(document.querySelector('.chain-badge--confirmed')).toBeNull();
    expect(screen.getByText(/never changes the comparison outcome/)).toBeInTheDocument();
    expect(document.querySelector('body')?.textContent ?? '').not.toMatch(/Success|Confirmed successfully/i);
  });

  it('shows NOT_REQUESTED clearly when recording is disabled', async () => {
    setMockConfig({ chain: 'NOT_REQUESTED' });
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Not recorded on-chain')).toBeInTheDocument();
    expect(screen.getByText(/Blockchain recording is not enabled/)).toBeInTheDocument();
  });

  it('does not fabricate a transaction hash when the chain was unreachable', async () => {
    setMockConfig({ chain: 'FAILED:RPC_UNAVAILABLE' });
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    await screen.findByText('On-chain recording failed');
    expect(screen.queryByText('Transaction hash')).not.toBeInTheDocument();
  });

  it('does not render hashes at all when recording was not requested', async () => {
    setMockConfig({ chain: 'NOT_REQUESTED' });
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Not recorded on-chain');
    expect(screen.queryByText('Transaction hash')).not.toBeInTheDocument();
    expect(screen.queryByText('Event digest')).not.toBeInTheDocument();
  });

  it('explains a pending submission without implying it succeeded', async () => {
    setMockConfig({ chain: 'PENDING' });
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('On-chain recording pending')).toBeInTheDocument();
    expect(screen.getByText(/waiting for confirmation/)).toBeInTheDocument();
    expect(screen.queryByText('Confirmed at')).not.toBeInTheDocument();
  });

  it('shows the required empty-state copy when no record exists', async () => {
    server.use(
      http.get(`*/api/v1/verifications/${TEST_VERIFICATION_ID}/blockchain`, () => HttpResponse.json(null))
    );
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('No blockchain record available')).toBeInTheDocument();
  });

  it('renders the synthetic data banner', async () => {
    renderWithRouter(<BlockchainReceiptPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Blockchain receipt');
    expect(screen.getByText('SYNTHETIC DEMO DATA')).toBeInTheDocument();
  });
});