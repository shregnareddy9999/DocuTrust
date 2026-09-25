import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments } from '../state/recentDocuments';
import { useShellSearch } from '../state/shellSearch';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { DocumentsIcon } from '../components/icons';

function countStatus(
  rows: { currentStatus: string | null }[],
  match: (status: string) => boolean
): number {
  return rows.filter((row) => row.currentStatus && match(row.currentStatus)).length;
}

export function DashboardPage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const search = useShellSearch();

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return rows;
    return rows.filter((row) =>
      [row.fileName, row.categoryLabel, row.documentId]
        .join(' ')
        .toLowerCase()
        .includes(query)
    );
  }, [rows, search]);

  const stats = useMemo(
    () => ({
      matched: countStatus(rows, (status) => status === 'VERIFIED_MATCH'),
      needsReview: countStatus(
        rows,
        (status) => status === 'REVIEW_REQUIRED' || status === 'INTEGRITY_MISMATCH'
      ),
      noReference: countStatus(rows, (status) => status === 'NO_TRUSTED_RECORD'),
    }),
    [rows]
  );

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading this browser session…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (rows.length === 0) {
    return (
      <div className="page dashboard-page">
        <h1>Dashboard</h1>
        <p className="page-intro">Documents opened in this browser session.</p>
        <EmptyState
          icon={<DocumentsIcon />}
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
    <div className="page dashboard-page">
      <h1>Dashboard</h1>
      <p className="page-intro">Documents opened in this browser session.</p>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.matched}</span>
          <span className="stat-label">Matched</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.needsReview}</span>
          <span className="stat-label">Needs review</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.noReference}</span>
          <span className="stat-label">No reference</span>
        </div>
      </div>

      <section className="card" aria-label="Recent documents">
        <h2>Recent documents</h2>
        {filtered.length === 0 ? (
          <EmptyState
            title="No matches"
            message="No documents in this browser session match your search."
          />
        ) : (
          <ul className="doc-list">
            {filtered.map((row) => (
              <li key={row.documentId} className="doc-list-row">
                <Link
                  to={
                    row.currentVerificationId
                      ? `/verifications/${row.currentVerificationId}`
                      : `/documents/${row.documentId}`
                  }
                  className="doc-list-main"
                >
                  <span className="doc-list-name">{row.fileName}</span>
                  <span className="doc-list-meta">
                    <span>{row.categoryLabel}</span>
                    <span aria-hidden="true"> · </span>
                    <span>{new Date(row.uploadedAt).toLocaleDateString()}</span>
                  </span>
                </Link>
                {row.currentStatus ? (
                  <StatusBadge status={row.currentStatus} />
                ) : (
                  <span className="doc-list-none">No comparison yet</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}