import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { getBlockchain } from '../api/verifications';
import { useRecentDocuments } from '../state/recentDocuments';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { BlockchainIcon, SearchIcon } from '../components/icons';
import type { BlockchainResponse } from '../types/api';

type LookupState =
  | { status: 'idle' }
  | { status: 'searching' }
  | { status: 'matched'; receipt: BlockchainResponse }
  | { status: 'not_found' };

export function BlockchainTxVerifyPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const [txHash, setTxHash] = useState('');
  const [lookup, setLookup] = useState<LookupState>({ status: 'idle' });

  const verificationIds = useMemo(() => {
    const ids = new Set<string>();
    for (const row of rows) {
      for (const history of row.history) {
        ids.add(history.verificationId);
      }
    }
    return Array.from(ids);
  }, [rows]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedHash = txHash.trim().toLowerCase();
    if (!normalizedHash) {
      setLookup({ status: 'not_found' });
      return;
    }

    setLookup({ status: 'searching' });

    const settled = await Promise.allSettled(
      verificationIds.map((verificationId) => getBlockchain(verificationId))
    );

    const receipt = settled
      .filter((item): item is PromiseFulfilledResult<BlockchainResponse> => item.status === 'fulfilled')
      .map((item) => item.value)
      .find(
        (candidate) =>
          candidate.recording_status === 'CONFIRMED' &&
          candidate.transaction_hash?.trim().toLowerCase() === normalizedHash
      );

    setLookup(receipt ? { status: 'matched', receipt } : { status: 'not_found' });
  }

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading blockchain receipts..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  return (
    <div className="page blockchain-tx-verify-page">
      <div className="actions" style={{ justifyContent: 'space-between' }}>
        <Link to="/blockchain-receipts" className="button button--secondary">
          Back to receipts
        </Link>
      </div>

      <h1>Verify Blockchain</h1>
      <p className="page-intro">
        Search recorded receipt data by transaction hash. A match is based on an existing blockchain
        receipt returned by the app, not on format alone.
      </p>

      <section className="card" aria-label="Transaction hash search">
        <form className="tx-search-form" onSubmit={onSubmit}>
          <label className="form-field">
            <span>Transaction hash</span>
            <input
              type="search"
              value={txHash}
              onChange={(event) => setTxHash(event.target.value)}
              placeholder="Paste transaction hash"
              style={{ fontFamily: 'var(--mono)' }}
              aria-label="Transaction hash"
            />
          </label>
          <button type="submit" className="button button--primary" disabled={lookup.status === 'searching'}>
            <SearchIcon />
            {lookup.status === 'searching' ? 'Searching...' : 'Search'}
          </button>
        </form>
      </section>

      {verificationIds.length === 0 ? (
        <EmptyState
          icon={<BlockchainIcon />}
          title="No blockchain receipts available"
          message="Upload and compare a document first, then return here to check its recorded transaction."
          action={
            <Link to="/verify" className="button button--primary">
              Verify a document
            </Link>
          }
        />
      ) : null}

      {lookup.status === 'matched' ? <ReceiptMatch receipt={lookup.receipt} /> : null}

      {lookup.status === 'not_found' ? (
        <section className="card" aria-live="polite">
          <h2>Invalid transaction ID</h2>
          <p className="note">
            No confirmed receipt available to this app matches that transaction hash.
          </p>
        </section>
      ) : null}
    </div>
  );
}

function ReceiptMatch({ receipt }: { receipt: BlockchainResponse }) {
  return (
    <section className="card" aria-live="polite" aria-label="Transaction receipt details">
      <div className="result-status-row">
        <span className="result-label">Receipt is valid</span>
        <BlockchainStatusBadge blockchain={receipt} />
      </div>
      <div className="receipt-row">
        <span className="receipt-label">Verification ID</span>
        <span className="receipt-value">{receipt.verification_id}</span>
      </div>
      {receipt.transaction_hash ? (
        <div className="receipt-row">
          <span className="receipt-label">Transaction hash</span>
          <span className="receipt-value">{receipt.transaction_hash}</span>
        </div>
      ) : null}
      {receipt.chain_id !== null ? (
        <div className="receipt-row">
          <span className="receipt-label">Chain ID</span>
          <span className="receipt-value">{receipt.chain_id}</span>
        </div>
      ) : null}
      {receipt.contract_address ? (
        <div className="receipt-row">
          <span className="receipt-label">Contract address</span>
          <span className="receipt-value">{receipt.contract_address}</span>
        </div>
      ) : null}
      {receipt.event_digest ? (
        <div className="receipt-row">
          <span className="receipt-label">Event digest</span>
          <span className="receipt-value">{receipt.event_digest}</span>
        </div>
      ) : null}
      {receipt.submitted_at ? (
        <div className="receipt-row">
          <span className="receipt-label">Submitted at</span>
          <span className="receipt-value">{new Date(receipt.submitted_at).toLocaleString()}</span>
        </div>
      ) : null}
      {receipt.confirmed_at ? (
        <div className="receipt-row">
          <span className="receipt-label">Confirmed at</span>
          <span className="receipt-value">{new Date(receipt.confirmed_at).toLocaleString()}</span>
        </div>
      ) : null}
    </section>
  );
}
