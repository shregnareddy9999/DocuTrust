import { beforeEach, describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BlockchainTxVerifyPage } from './BlockchainTxVerifyPage';
import { renderWithRouter } from '../test/render';
import { addRecentDocument, clearRecentDocuments } from '../state/recentDocuments';
import { resetMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';

const DOC_ID = 'doc-demo-0001';
const ROUTE = '/blockchain-receipts/verify-tx';
const TX_HASH = '0x6b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2';

async function renderPageWithDocument() {
  addRecentDocument(DOC_ID);
  renderWithRouter(<BlockchainTxVerifyPage />, { route: ROUTE, path: ROUTE });
  await screen.findByRole('searchbox', { name: 'Transaction hash' });
}

describe('BlockchainTxVerifyPage', () => {
  beforeEach(() => {
    resetMockConfig();
    resetMockCounters();
    clearRecentDocuments();
  });

  it('shows receipt details and valid receipt wording for an exact transaction hash match', async () => {
    await renderPageWithDocument();

    await userEvent.type(screen.getByRole('searchbox', { name: 'Transaction hash' }), TX_HASH);
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(await screen.findByText('Receipt is valid')).toBeInTheDocument();
    expect(screen.getAllByText('Transaction hash').length).toBeGreaterThan(1);
    expect(screen.getByText(TX_HASH)).toBeInTheDocument();
    expect(screen.getByText('Contract address')).toBeInTheDocument();
  });

  it('shows invalid transaction wording for an unknown hash', async () => {
    await renderPageWithDocument();

    await userEvent.type(
      screen.getByRole('searchbox', { name: 'Transaction hash' }),
      '0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0'
    );
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(await screen.findByText('Invalid transaction ID')).toBeInTheDocument();
    expect(screen.queryByText('Receipt is valid')).not.toBeInTheDocument();
  });

  it('does not treat an incomplete hash as a matching receipt', async () => {
    await renderPageWithDocument();

    await userEvent.type(screen.getByRole('searchbox', { name: 'Transaction hash' }), TX_HASH.slice(0, 20));
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(await screen.findByText('Invalid transaction ID')).toBeInTheDocument();
  });

  it('shows invalid transaction wording for an empty search', async () => {
    await renderPageWithDocument();

    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(await screen.findByText('Invalid transaction ID')).toBeInTheDocument();
  });
});
