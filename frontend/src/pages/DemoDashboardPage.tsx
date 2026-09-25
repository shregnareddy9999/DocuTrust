import { useEffect } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useDocument } from '../state/useDocument';
import { useVerification } from '../state/useVerification';
import { useRecentDocumentIds } from '../state/recentDocuments';
import { StatusBadge } from '../components/StatusBadge';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { FieldComparisonTable } from '../components/FieldComparisonTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { safeMessage } from '../utils/messages';
import { STATUS_EXPLANATIONS } from '../utils/resultCopy';
import { buildFieldLabels } from '../utils/fields';
import { DemoIcon } from '../components/icons';

export function DemoDashboardPage() {
  const { documentId } = useParams();
  const recentIds = useRecentDocumentIds();

  const {
    document,
    extraction,
    documentTypes,
    loading,
    error,
    clearError,
    fetchDocumentTypes,
    fetchDocument,
    fetchExtraction,
  } = useDocument();
  const {
    verification,
    blockchain,
    history,
    loading: verifyLoading,
    error: verifyError,
    clearError: clearVerifyError,
    fetchVerification,
    fetchHistory,
    fetchBlockchain,
  } = useVerification();

  useEffect(() => {
    clearError();
    clearVerifyError();
    fetchDocumentTypes();
  }, [clearError, clearVerifyError, fetchDocumentTypes]);

  useEffect(() => {
    if (documentId) {
      fetchDocument(documentId);
      fetchExtraction(documentId);
      fetchHistory(documentId);
    }
  }, [documentId, fetchDocument, fetchExtraction, fetchHistory]);

  useEffect(() => {
    const current = history?.verifications.find((item) => item.is_current);
    if (current) {
      fetchVerification(current.verification_id);
      fetchBlockchain(current.verification_id);
    }
  }, [history, fetchVerification, fetchBlockchain]);

  if (!documentId) {
    const mostRecent = recentIds[0];
    if (mostRecent) {
      return <Navigate to={`/demo/${mostRecent}`} replace />;
    }
    return (
      <div className="page">
        <EmptyState
          icon={<DemoIcon />}
          title="No documents yet"
          message="Verify a document first so the demo has something to project."
          action={
            <Link to="/verify" className="button button--primary">
              Verify a document
            </Link>
          }
        />
      </div>
    );
  }

  const fieldLabels = buildFieldLabels(documentTypes);
  const categoryLabel =
    documentTypes.find((type) => type.category === document?.category)?.label ?? document?.category ?? '';
  const needsReview =
    verification?.status === 'REVIEW_REQUIRED' || verification?.status === 'INTEGRITY_MISMATCH';

  return (
    <div className="page demo-dashboard">
      <h1>PS21 Live Demo</h1>
      <p className="page-intro">
        Projected outcome for <strong>{documentId}</strong>. This is a synthetic demonstration — every
        reference on screen is demo data.
      </p>

      {error ? <ErrorState message={safeMessage(error)} onRetry={() => fetchDocument(documentId)} /> : null}
      {verifyError ? (
        <ErrorState message={safeMessage(verifyError)} onRetry={() => fetchHistory(documentId)} />
      ) : null}

      <section className="card demo-section" aria-label="Document">
        <h2>Document</h2>
        {loading && !document ? (
          <LoadingState message="Loading document…" />
        ) : document ? (
          <div className="demo-doc-meta">
            <span className="doc-list-name">{document.original_filename}</span>
            <span className="doc-list-meta">
              {categoryLabel || document.category} · {new Date(document.uploaded_at).toLocaleDateString()}
            </span>
          </div>
        ) : (
          <p className="note">The document could not be loaded.</p>
        )}
      </section>

      <section className="card demo-section" aria-label="Extracted fields">
        <h2>Extracted fields</h2>
        {loading && !extraction ? (
          <LoadingState message="Reading document…" />
        ) : extraction && Object.keys(extraction.extracted_fields).length > 0 ? (
          <div className="table-scroll">
            <table className="fields-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(extraction.extracted_fields).map(([name, field]) => (
                  <tr key={name}>
                    <td>{fieldLabels[name] ?? name}</td>
                    <td>{field.value ?? 'Not found'}</td>
                    <td>{field.confidence !== null ? `${Math.round(field.confidence * 100)}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="note">No extraction available for this document.</p>
        )}
      </section>

      <section className="card demo-section" aria-label="Comparison outcome">
        <h2>Comparison outcome</h2>
        {verifyLoading && !verification ? (
          <LoadingState message="Loading the latest comparison…" />
        ) : verification ? (
          <>
            <div className="result-status-row">
              <span className="result-label">Verification status</span>
              <StatusBadge status={verification.status} />
            </div>
            <div className="result-status-row">
              <span className="result-label">On-chain recording</span>
              <BlockchainStatusBadge blockchain={blockchain} />
            </div>
            <p className="demo-explanation">{STATUS_EXPLANATIONS[verification.status]}</p>
            <FieldComparisonTable comparisons={verification.field_comparisons} labels={fieldLabels} />
          </>
        ) : (
          <p className="note">Run a comparison from the Verify Document screen to see the outcome here.</p>
        )}
      </section>

      <div className="actions">
        {verification ? (
          <>
            <Link to={`/verifications/${verification.verification_id}`} className="button button--primary">
              Open full result
            </Link>
            {needsReview ? (
              <Link
                to={`/verifications/${verification.verification_id}/review`}
                className="button button--primary"
              >
                Review
              </Link>
            ) : null}
            <Link to={`/verifications/${verification.verification_id}/blockchain`} className="button button--secondary">
              Blockchain receipt
            </Link>
          </>
        ) : null}
        <Link to="/verify" className="button button--ghost">
          Verify another document
        </Link>
      </div>
    </div>
  );
}