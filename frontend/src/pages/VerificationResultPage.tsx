import { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useVerification } from '../state/useVerification';
import { useDocument } from '../state/useDocument';
import { StatusBadge } from '../components/StatusBadge';
import { BlockchainStatusBadge } from '../components/BlockchainStatusBadge';
import { SyntheticDataBanner } from '../components/SyntheticDataBanner';
import { PipelineTrack } from '../components/PipelineTrack';
import { FieldComparisonTable } from '../components/FieldComparisonTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { safeMessage } from '../utils/messages';
import { STATUS_EXPLANATIONS } from '../utils/resultCopy';
import { buildFieldLabels, fieldLabel } from '../utils/fields';

export function VerificationResultPage() {
  const { verificationId = '' } = useParams();
  const navigate = useNavigate();
  const {
    verification,
    history,
    blockchain,
    loading,
    error,
    fetchVerification,
    fetchHistory,
    fetchBlockchain,
    clearError,
  } = useVerification();
  const { documentTypes, fetchDocumentTypes } = useDocument();

  useEffect(() => {
    clearError();
    fetchVerification(verificationId);
    fetchBlockchain(verificationId);
  }, [verificationId, fetchVerification, fetchBlockchain, clearError]);

  useEffect(() => {
    if (verification?.document_id) {
      fetchHistory(verification.document_id);
    }
  }, [verification?.document_id, fetchHistory]);

  useEffect(() => {
    fetchDocumentTypes();
  }, [fetchDocumentTypes]);

  function reload() {
    clearError();
    fetchVerification(verificationId);
    fetchBlockchain(verificationId);
  }

  if (loading && !verification) {
    return <LoadingState message="Loading verification result…" />;
  }

  if (error && !verification) {
    return <ErrorState message={safeMessage(error)} onRetry={reload} />;
  }

  if (!verification) {
    return (
      <EmptyState
        title="No verification result"
        message="There is no comparison result to show for this verification. It may have been removed."
      />
    );
  }

  const needsReview =
    verification.status === 'REVIEW_REQUIRED' || verification.status === 'INTEGRITY_MISMATCH';

  const fieldLabels = buildFieldLabels(documentTypes);
  const mismatchFields = verification.field_comparisons.filter((cmp) => !cmp.matched);

  return (
    <div className="page verification-result-page">
      <SyntheticDataBanner />
      <h1>Comparison result</h1>

      <PipelineTrack
        current={
          needsReview
            ? 'review'
            : verification.status === 'PENDING'
              ? 'compare'
              : 'record'
        }
      />

      {error ? <ErrorState message={safeMessage(error)} onRetry={reload} /> : null}

      <section className="card result-status-card" aria-label="Comparison status">
        <div className="result-status-row">
          <span className="result-label">Verification status</span>
          <StatusBadge status={verification.status} />
        </div>
        <div className="result-status-row">
          <span className="result-label">On-chain recording</span>
          <BlockchainStatusBadge blockchain={blockchain} />
        </div>
        <p className="result-explanation">{STATUS_EXPLANATIONS[verification.status]}</p>
      </section>

      {mismatchFields.length > 0 ? (
        <section className="card" aria-label="Mismatched fields">
          <h2>Mismatch found in:</h2>
          <ul className="mismatch-fields">
            {mismatchFields.map((cmp) => (
              <li key={cmp.field}>{fieldLabel(cmp.field, fieldLabels)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {verification.reason_codes.length > 0 || verification.rule_results.length > 0 ? (
        <section className="card" aria-label="Why this result">
          <h2>Why this result</h2>
          {verification.rule_results.map((rule) => (
            <div key={rule.rule_id} className={rule.passed ? 'rule-result rule-result--pass' : 'rule-result rule-result--fail'}>
              <strong>{rule.rule_id}</strong> — {rule.reason || (rule.passed ? 'Passed' : 'Failed')}
            </div>
          ))}
        </section>
      ) : null}

      <section className="card" aria-label="Field comparison">
        <h2>Field-by-field comparison</h2>
        <FieldComparisonTable comparisons={verification.field_comparisons} labels={fieldLabels} />
      </section>

      {history && history.verifications.length > 0 ? (
        <section className="card" aria-label="Verification history">
          <h2>Verification history</h2>
          <div className="table-scroll">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Review actions</th>
                  <th>Position</th>
                </tr>
              </thead>
              <tbody>
                {history.verifications.map((item) => (
                  <tr key={item.verification_id} className={item.is_current ? 'row--current' : undefined}>
                    <td>
                      <StatusBadge status={item.status} />
                    </td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>{item.review_action_count}</td>
                    <td>{item.is_current ? 'Current result' : 'Earlier'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <div className="actions">
        {needsReview ? (
          <button
            type="button"
            className="button button--primary"
            onClick={() => navigate(`/verifications/${verificationId}/review`)}
          >
            Review this document
          </button>
        ) : null}
        <Link to={`/verifications/${verificationId}/blockchain`} className="button button--secondary">
          View blockchain receipt
        </Link>
        <Link to="/verify" className="button button--ghost">
          Verify another document
        </Link>
      </div>
    </div>
  );
}