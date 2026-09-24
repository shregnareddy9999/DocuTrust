import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useVerification } from '../state/useVerification';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { PipelineTrack } from '../components/PipelineTrack';
import { SyntheticDataBanner } from '../components/SyntheticDataBanner';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { safeMessage, translateBlockchainError } from '../utils/messages';
import { ShieldIcon } from '../components/icons';
import type { BlockchainResponse } from '../types/api';

export function BlockchainReceiptPage() {
  const { verificationId = '' } = useParams();
  const { blockchain, loading, error, fetchBlockchain, clearError } = useVerification();

  useEffect(() => {
    clearError();
    fetchBlockchain(verificationId);
  }, [verificationId, fetchBlockchain, clearError]);

  function reload() {
    clearError();
    fetchBlockchain(verificationId);
  }

  if (loading && !blockchain) {
    return <LoadingState message="Loading on-chain record…" />;
  }

  if (error && !blockchain) {
    return <ErrorState message={safeMessage(error)} onRetry={reload} />;
  }

  if (!blockchain) {
    return (
      <div className="page">
        <EmptyState
          icon={<ShieldIcon />}
          title="No blockchain record available"
          message="There is no on-chain record for this verification."
          action={
            <button type="button" className="button button--primary" onClick={reload}>
              Try again
            </button>
          }
        />
      </div>
    );
  }

  const failedError = blockchain.recording_status === 'FAILED'
    ? translateBlockchainError(getErrorCode(blockchain))
    : null;

  return (
    <div className="page blockchain-receipt-page">
      <SyntheticDataBanner />
      <h1>Blockchain receipt</h1>

      <PipelineTrack current="record" />

      {error ? <ErrorState message={safeMessage(error)} onRetry={reload} /> : null}

      <section className="card" aria-label="On-chain recording status">
        <div className="result-status-row">
          <span className="result-label">Recording status</span>
          <BlockchainStatusBadge blockchain={blockchain} />
        </div>

        {blockchain.recording_status === 'NOT_REQUESTED' ? (
          <p className="note">
            Blockchain recording is not enabled for this environment, so no event was submitted. This is
            a normal state and does not change the verification result.
          </p>
        ) : null}

        {blockchain.recording_status === 'PENDING' ? (
          <p className="note">
            The on-chain submission is waiting for confirmation. Refresh this page to check the latest
            state. It is tracked separately from the comparison result.
          </p>
        ) : null}

        {blockchain.recording_status === 'FAILED' ? (
          <div className="chain-failure" role="alert">
            <p>{failedError ?? 'The on-chain recording could not be completed.'}</p>
            <p className="note">
              This affects only the on-chain record. The verification result itself is unaffected —
              a failed chain submission never changes the comparison outcome.
            </p>
          </div>
        ) : null}
      </section>

      {blockchain.recording_status !== 'NOT_REQUESTED' ? (
        <section className="card" aria-label="Receipt details">
          <h2>Receipt details</h2>
          <ReceiptRow label="Verification ID" value={blockchain.verification_id} />
          {blockchain.transaction_hash ? (
            <ReceiptRow label="Transaction hash" value={shrinkHash(blockchain.transaction_hash)} />
          ) : null}
          {blockchain.chain_id !== null ? <ReceiptRow label="Chain ID" value={String(blockchain.chain_id)} /> : null}
          {blockchain.contract_address ? (
            <ReceiptRow label="Contract address" value={shrinkHash(blockchain.contract_address)} />
          ) : null}
          {blockchain.event_digest ? <ReceiptRow label="Event digest" value={shrinkHash(blockchain.event_digest)} /> : null}
          {blockchain.submitted_at ? (
            <ReceiptRow label="Submitted at" value={new Date(blockchain.submitted_at).toLocaleString()} />
          ) : null}
          {blockchain.confirmed_at ? (
            <ReceiptRow label="Confirmed at" value={new Date(blockchain.confirmed_at).toLocaleString()} />
          ) : null}
        </section>
      ) : null}

      <section className="card" aria-label="What this record proves">
        <h2>What this record proves — and what it does not</h2>
        <p>
          The on-chain event records that <strong>this verification outcome</strong> was reached at a
          specific time and has not been silently altered since. It is an audit trail for our own
          result.
        </p>
        <p className="note">
          It is <strong>not</strong> a document hash and makes no claim about the uploaded file itself
          or who issued it. The chain never evaluates a real-world document.
        </p>
      </section>

      <div className="actions">
        <Link to={`/verifications/${verificationId}`} className="button button--primary">
          Back to comparison result
        </Link>
        <Link to="/verify" className="button button--ghost">
          Verify another document
        </Link>
      </div>
    </div>
  );
}

function ReceiptRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="receipt-row">
      <span className="receipt-label">{label}</span>
      <span className="receipt-value">{value}</span>
    </div>
  );
}

function getErrorCode(blockchain: BlockchainResponse): BlockchainResponse['error_code'] {
  return blockchain.error_code;
}

function shrinkHash(hash: string): string {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 10)}…${hash.slice(-8)}`;
}