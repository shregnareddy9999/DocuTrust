import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { BlockchainStatusBadge } from './BlockchainStatusBadge';
import type { BlockchainResponse } from '../types/api';

function badge(recording_status: BlockchainResponse['recording_status']): BlockchainResponse {
  return {
    verification_id: 'ver-1',
    recording_status,
    chain_id: null,
    contract_address: null,
    transaction_hash: null,
    event_digest: null,
    submitted_at: null,
    confirmed_at: null,
    error_code: null,
  };
}

describe('BlockchainStatusBadge', () => {
  it('renders the confirmed label', () => {
    const { getByText } = render(<BlockchainStatusBadge blockchain={badge('CONFIRMED')} />);
    expect(getByText('Verification outcome recorded on-chain')).toBeInTheDocument();
  });

  it('renders the not-requested label', () => {
    const { getByText } = render(<BlockchainStatusBadge blockchain={badge('NOT_REQUESTED')} />);
    expect(getByText('Not recorded on-chain')).toBeInTheDocument();
  });

  it('renders the pending label', () => {
    const { getByText } = render(<BlockchainStatusBadge blockchain={badge('PENDING')} />);
    expect(getByText('On-chain recording pending')).toBeInTheDocument();
  });

  it('renders the failed label without claiming success', () => {
    const { getByText } = render(<BlockchainStatusBadge blockchain={badge('FAILED')} />);
    expect(getByText('On-chain recording failed')).toBeInTheDocument();
  });
});