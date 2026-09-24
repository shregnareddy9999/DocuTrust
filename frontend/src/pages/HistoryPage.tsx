import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments, type RecentDocumentRow } from '../state/recentDocuments';
import { useShellSearch } from '../state/shellSearch';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { HistoryIcon } from '../components/icons';
import type { VerificationStatus } from '../types/api';

interface HistoryEntry {
  verificationId: string;
  documentName: string;
  categoryLabel: string;
  status: VerificationStatus;
  isCurrent: boolean;
  createdAt: string;
  reviewedBy: string | null;
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
  }));
}

export function HistoryPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const search = useShellSearch();

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

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading this browser session…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (entries.length === 0) {
    return (
      <div className="page history-page">
        <h1>History</h1>
        <p className="page-intro">Verification outcomes for documents opened in this browser session.</p>
        <EmptyState
          icon={<HistoryIcon />}
          title="No verification history yet"
          message="Comparison results will appear here."
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
      <p className="page-intro">Verification outcomes for documents opened in this browser session.</p>

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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
    </div>
  );
}