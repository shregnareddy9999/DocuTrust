import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments } from '../state/recentDocuments';
import { useShellSearch } from '../state/shellSearch';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { ReviewIcon } from '../components/icons';

const REVIEW_STATUSES = ['REVIEW_REQUIRED', 'INTEGRITY_MISMATCH'];

export function ReviewQueuePage() {
  const { rows, loading, error, reload } = useRecentDocuments();
  const search = useShellSearch();

  const queued = useMemo(() => {
    const needsReview = rows.filter(
      (row) => row.currentStatus && REVIEW_STATUSES.includes(row.currentStatus)
    );
    const query = search.trim().toLowerCase();
    if (!query) return needsReview;
    return needsReview.filter((row) =>
      [row.fileName, row.categoryLabel, row.documentId]
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

  return (
    <div className="page review-queue-page">
      <h1>Review Queue</h1>
      <p className="page-intro">
        Documents opened in this browser session whose outcome needs a human decision.
      </p>

      {queued.length === 0 ? (
        <EmptyState
          icon={<ReviewIcon />}
          title="No documents need review"
          message="When a comparison needs a human decision, it will appear here."
          action={
            <Link to="/verify" className="button button--primary">
              Verify a document
            </Link>
          }
        />
      ) : (
        <section className="card" aria-label="Review queue">
          <div className="table-scroll">
            <table className="review-queue-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Category</th>
                  <th>Outcome</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {queued.map((row) => (
                  <tr key={row.documentId}>
                    <td className="doc-name">{row.fileName}</td>
                    <td>{row.categoryLabel}</td>
                    <td>
                      {row.currentStatus ? <StatusBadge status={row.currentStatus} /> : null}
                    </td>
                    <td>
                      {row.currentVerificationId ? (
                        <Link
                          to={`/verifications/${row.currentVerificationId}/review`}
                          className="button button--primary"
                        >
                          Review
                        </Link>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}