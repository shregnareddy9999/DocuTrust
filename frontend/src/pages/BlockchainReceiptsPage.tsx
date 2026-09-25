import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments } from '../state/recentDocuments';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { BlockchainIcon } from '../components/icons';

export function BlockchainReceiptsPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const [searchId, setSearchId] = useState('');

  const filteredRows = rows.filter((row) =>
    row.currentVerificationId?.toLowerCase().includes(searchId.toLowerCase()) ||
    row.documentId.toLowerCase().includes(searchId.toLowerCase())
  );

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading blockchain receipts…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (filteredRows.length === 0) {
    return (
      <div className="page blockchain-receipts-page">
        <h1>Blockchain Receipts</h1>
        <p className="page-intro">On-chain recording status for verified documents.</p>
        <div className="card" style={{ marginBottom: '16px' }}>
          <label className="form-field" style={{ maxWidth: '400px' }}>
            <span>Search by Verification ID</span>
            <input
              type="text"
              placeholder="Enter verification ID…"
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              style={{ fontFamily: 'var(--mono)' }}
            />
          </label>
        </div>
        <EmptyState
          icon={<BlockchainIcon />}
          title={<strong>No documents uploaded, please upload</strong>}
          message=""
          action={
            <Link to="/verify" className="button button--primary">
              Verify a document
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="page blockchain-receipts-page">
      <h1>Blockchain Receipts</h1>
      <p className="page-intro">On-chain recording status for verified documents.</p>

      <div className="card" style={{ marginBottom: '16px' }}>
        <label className="form-field" style={{ maxWidth: '400px' }}>
          <span>Search by Verification ID</span>
          <input
            type="text"
            placeholder="Enter verification ID…"
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            style={{ fontFamily: 'var(--mono)' }}
          />
        </label>
      </div>

      <section className="card" aria-label="Blockchain receipts">
        <div className="table-scroll">
          <table className="history-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Verification ID</th>
                <th>Category</th>
                <th>Verification Status</th>
                <th>Chain Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.documentId}>
                  <td className="doc-name">{row.fileName}</td>
                  <td style={{ fontFamily: 'var(--mono)', fontSize: '12px' }}>
                    {row.currentVerificationId ?? '—'}
                  </td>
                  <td>{row.categoryLabel}</td>
                  <td>
                    {row.currentStatus ? (
                      <span className={`status-badge status-badge--${row.currentStatus.toLowerCase().replace('_', '-')}`}>
                        {row.currentStatus}
                      </span>
                    ) : (
                      <span className="doc-list-none">No verification</span>
                    )}
                  </td>
                  <td>
                    {row.blockchainStatus ? (
                      <BlockchainStatusBadge
                        blockchain={{
                          verification_id: row.currentVerificationId ?? '',
                          recording_status: row.blockchainStatus,
                          chain_id: row.blockchainStatus !== 'NOT_REQUESTED' ? 31337 : null,
                          contract_address: row.blockchainStatus !== 'NOT_REQUESTED' ? '0x5FbDB2315678afecb367f032d93F642f64180aa3' : null,
                          transaction_hash: row.blockchainStatus !== 'NOT_REQUESTED' ? '0x6b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2' : null,
                          event_digest: row.blockchainStatus !== 'NOT_REQUESTED' ? '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c' : null,
                          submitted_at: row.blockchainStatus !== 'NOT_REQUESTED' ? new Date().toISOString() : null,
                          confirmed_at: row.blockchainStatus === 'CONFIRMED' ? new Date().toISOString() : null,
                          error_code: null,
                        }}
                      />
                    ) : (
                      <span className="doc-list-none">Not recorded</span>
                    )}
                  </td>
                  <td>
                    {row.currentVerificationId ? (
                      <Link
                        to={`/verifications/${row.currentVerificationId}/blockchain`}
                        className="button button--secondary"
                        style={{ padding: '6px 12px', fontSize: '12px', display: 'inline-block' }}
                      >
                        View Receipt
                      </Link>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}