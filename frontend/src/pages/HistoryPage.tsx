import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments, type RecentDocumentRow } from '../state/recentDocuments';
import { useShellSearch } from '../state/shellSearch';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { HistoryIcon, TrashIcon } from '../components/icons';
import type { VerificationStatus } from '../types/api';
import { hideVerification } from '../state/recentDocuments';
import { ConfirmModal } from '../components/ConfirmModal';

interface HistoryEntry {
  verificationId: string;
  documentName: string;
  categoryLabel: string;
  status: VerificationStatus;
  isCurrent: boolean;
  createdAt: string;
  reviewedBy: string | null;
  documentId: string;
}

function entriesFor(row: RecentDocumentRow): HistoryEntry[] {
  return row.history.map((item) => ({
    verificationId: item.verificationId,
    documentName: row.fileName,
    categoryLabel: row.categoryLabel,
    status: item.status,
    isCurrent: item.isCurrent,
    createdAt: item.createdAt,
    reviewedBy: item.reviewedBy,
    documentId: row.documentId,
  }));
}

export function HistoryPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const search = useShellSearch();
  const [deleteTarget, setDeleteTarget] = useState<{ documentId: string; verificationId: string } | null>(null);

  const entries = useMemo(() => {
    const all = rows.flatMap(entriesFor);
    const query = search.trim().toLowerCase();
    if (!query) return all;
    return all.filter((entry) =>
      [entry.documentName, entry.categoryLabel, entry.verificationId]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [rows, search]);

  const handleDeleteClick = (documentId: string, verificationId: string) => {
    setDeleteTarget({ documentId, verificationId });
  };

  const handleDeleteConfirm = () => {
    if (deleteTarget) {
      hideVerification(deleteTarget.documentId, deleteTarget.verificationId);
      setDeleteTarget(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteTarget(null);
  };

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading your history…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (entries.length === 0) {
    return (
      <div className="page history-page">
        <h1>History</h1>
        <p className="page-intro">Verification outcomes for documents in your account.</p>
        <EmptyState
          icon={<HistoryIcon />}
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
    <div className="page history-page">
      <h1>History</h1>
      <p className="page-intro">Verification outcomes for documents in your account.</p>

      <section className="card" aria-label="Verification history">
          <div className="table-scroll">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Outcome</th>
                  <th>Reviewed by</th>
                  <th>Created</th>
                  <th>Position</th>
                  <th />
                  <th />
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.verificationId} className={entry.isCurrent ? 'row--current' : undefined}>
                    <td className="doc-name">{entry.documentName}</td>
                    <td>
                      <StatusBadge status={entry.status} />
                    </td>
                    <td>{entry.reviewedBy ?? '—'}</td>
                    <td>{new Date(entry.createdAt).toLocaleDateString()}</td>
                    <td>{entry.isCurrent ? 'Current result' : 'Earlier'}</td>
                    <td>
                      <Link to={`/verifications/${entry.verificationId}`} className="link">
                        View
                      </Link>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="button button--ghost"
                        onClick={() => handleDeleteClick(entry.documentId, entry.verificationId)}
                        aria-label={`Delete verification for ${entry.documentName}`}
                        style={{ padding: '4px 8px', fontSize: '12px' }}
                      >
                        <TrashIcon />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      <ConfirmModal
        isOpen={deleteTarget !== null}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete verification"
        message="Are you sure you want to delete this verification from history? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
      />
    </div>
  );
}