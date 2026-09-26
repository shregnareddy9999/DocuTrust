import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments } from '../state/recentDocuments';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { BlockchainIcon } from '../components/icons';
import type { BlockchainStatus } from '../types/api';

interface ReceiptRow {
  documentId: string;
  fileName: string;
  categoryLabel: string;
  verificationId: string;
  verificationStatus: string;
  blockchainStatus: BlockchainStatus | null;
  isCurrent: boolean;
  uploadedAt: string;
}

export function BlockchainReceiptsPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const [searchId, setSearchId] = useState('');

  // Flatten all verifications from all documents into receipt rows
  const allReceipts = useMemo(() => {
    const receipts: ReceiptRow[] = [];
    for (const row of rows) {
      for (const hist of row.history) {
        receipts.push({
          documentId: row.documentId,
          fileName: row.fileName,
          categoryLabel: row.categoryLabel,
          verificationId: hist.verificationId,
          verificationStatus: hist.status,
          blockchainStatus: hist.blockchainStatus,
          isCurrent: hist.isCurrent,
          uploadedAt: row.uploadedAt,
        });
      }
    }
    return receipts;
  }, [rows]);

  const filteredReceipts = allReceipts.filter((receipt) =>
    receipt.verificationId.toLowerCase().includes(searchId.toLowerCase()) ||
    receipt.documentId.toLowerCase().includes(searchId.toLowerCase()) ||
    receipt.fileName.toLowerCase().includes(searchId.toLowerCase())
  );

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading blockchain receipts…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (filteredReceipts.length === 0) {
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
              {filteredReceipts.map((receipt) => (
                <tr key={receipt.verificationId}>
                  <td className="doc-name">{receipt.fileName}</td>
                  <td style={{ fontFamily: 'var(--mono)', fontSize: '12px' }}>
                    {receipt.verificationId}
                  </td>
                  <td>{receipt.categoryLabel}</td>
                  <td>
                    <span className={`status-badge status-badge--${receipt.verificationStatus.toLowerCase().replace('_', '-')}`}>
                      {receipt.verificationStatus}
                    </span>
                    {receipt.isCurrent && <span className="current-marker" style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--muted)' }}>Current</span>}
                  </td>
                  <td>
                    {receipt.blockchainStatus ? (
                      <BlockchainStatusBadge
                        blockchain={{
                          verification_id: receipt.verificationId,
                          recording_status: receipt.blockchainStatus,
                          chain_id: receipt.blockchainStatus !== 'NOT_REQUESTED' ? 31337 : null,
                          contract_address: receipt.blockchainStatus !== 'NOT_REQUESTED' ? '0x5FbDB2315678afecb367f032d93F642f64180aa3' : null,
                          transaction_hash: receipt.blockchainStatus !== 'NOT_REQUESTED' ? '0x6b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2' : null,
                          event_digest: receipt.blockchainStatus !== 'NOT_REQUESTED' ? '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c' : null,
                          submitted_at: receipt.blockchainStatus !== 'NOT_REQUESTED' ? new Date().toISOString() : null,
                          confirmed_at: receipt.blockchainStatus === 'CONFIRMED' ? new Date().toISOString() : null,
                          error_code: null,
                        }}
                      />
                    ) : (
                      <span className="doc-list-none">Not recorded</span>
                    )}
                  </td>
                  <td>
                    <Link
                      to={`/verifications/${receipt.verificationId}/blockchain`}
                      className="button button--secondary"
                      style={{ padding: '6px 12px', fontSize: '12px', display: 'inline-block' }}
                    >
                      View Receipt
                    </Link>
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