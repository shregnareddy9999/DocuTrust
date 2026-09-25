import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useRecentDocuments } from '../state/recentDocuments';
import { useShellSearch } from '../state/shellSearch';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { DocumentsIcon } from '../components/icons';

export function DocumentsPage() {
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

  if (loading && rows.length === 0) {
    return <LoadingState message="Loading this browser session…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (rows.length === 0) {
    return (
      <div className="page documents-page">
        <h1>Documents</h1>
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
    <div className="page documents-page">
      <h1>Documents</h1>
      <p className="page-intro">Documents opened in this browser session.</p>

      {filtered.length === 0 ? (
        <EmptyState
          title="No matches"
          message="No documents in this browser session match your search."
        />
      ) : (
        <section className="card" aria-label="Document list">
          <div className="table-scroll">
            <table className="documents-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Category</th>
                  <th>Uploaded</th>
                  <th>Current outcome</th>
                  <th>Reviewed by</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.documentId}>
                    <td className="doc-name">{row.fileName}</td>
                    <td>{row.categoryLabel}</td>
                    <td>{new Date(row.uploadedAt).toLocaleDateString()}</td>
                    <td>
                      {row.currentStatus ? (
                        <StatusBadge status={row.currentStatus} />
                      ) : (
                        <span className="doc-list-none">No comparison yet</span>
                      )}
                    </td>
                    <td>
                      {row.history.length > 0 && row.history[0].reviewedBy
                        ? row.history[0].reviewedBy
                        : '—'}
                    </td>
                    <td>
                      <Link to={`/documents/${row.documentId}`} className="link">
                        Open
                      </Link>
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