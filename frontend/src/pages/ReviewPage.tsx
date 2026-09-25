import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useVerification } from '../state/useVerification';
import { useDocument } from '../state/useDocument';
import { StatusBadge } from '../components/StatusBadge';
import { PipelineTrack } from '../components/PipelineTrack';
import { SyntheticDataBanner } from '../components/SyntheticDataBanner';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { safeMessage } from '../utils/messages';
import type { VerificationStatus } from '../types/api';

const ACTIONS = [
  { value: 'ACCEPT', label: 'Accept as read' },
  { value: 'CORRECT', label: 'Correct a value' },
  { value: 'UNRESOLVED', label: 'Could not resolve' },
] as const;

export function ReviewPage() {
  const { verificationId = '' } = useParams();
  const {
    verification,
    loading,
    error,
    reviewSubmitting,
    fetchVerification,
    submitReview,
    clearError,
  } = useVerification();
  const {
    extraction,
    documentTypes,
    loading: docLoading,
    error: docError,
    fetchExtraction,
    fetchDocumentTypes,
  } = useDocument();

  const [reviewerRef, setReviewerRef] = useState('');
  const [action, setAction] = useState<'ACCEPT' | 'CORRECT' | 'UNRESOLVED'>('ACCEPT');
  const [comment, setComment] = useState('');
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [submittedResult, setSubmittedResult] = useState<{ newStatus: string; newVerificationId: string } | null>(null);

  useEffect(() => {
    fetchVerification(verificationId);
  }, [verificationId, fetchVerification]);

  useEffect(() => {
    if (verification?.document_id) {
      fetchDocumentTypes();
      fetchExtraction(verification.document_id);
    }
  }, [verification?.document_id, fetchDocumentTypes, fetchExtraction]);

  function fieldLabel(fieldName: string): string {
    for (const type of documentTypes) {
      const match = type.fields.find((f) => f.name === fieldName);
      if (match) return match.label;
    }
    return fieldName;
  }

  async function handleSubmit() {
    if (!reviewerRef.trim()) return;
    clearError();
    try {
      const response = await submitReview(verificationId, {
        reviewer_ref: reviewerRef.trim(),
        action,
        corrections: action === 'CORRECT' ? changedCorrections() : undefined,
        comment: comment.trim(),
      });
      setSubmittedResult({ newStatus: response.new_status, newVerificationId: response.new_verification_id });
    } catch {
      // error surfaced via error state
    }
  }

  function changedCorrections(): Record<string, string> {
    const changed: Record<string, string> = {};
    for (const [name, value] of Object.entries(corrections)) {
      const original = extractedFields[name]?.value ?? '';
      if ((value ?? '').trim() !== original.trim()) {
        changed[name] = value;
      }
    }
    return changed;
  }

  if (submittedResult) {
    return (
      <div className="page review-page">
        <SyntheticDataBanner />
        <section className="card review-complete">
          <h1>Review recorded</h1>
          <p>
            A new verification record was created for this document rather than editing the previous
            one. The original OCR values and the earlier outcome remain in the history.
          </p>
          <div className="result-status-row">
            <span className="result-label">New status</span>
            <StatusBadge status={submittedResult.newStatus as VerificationStatus} />
          </div>
          {submittedResult.newStatus === 'VERIFIED_MATCH' && action === 'CORRECT' ? (
            <p className="review-corrected-note">
              This match is <strong>(reviewer-corrected)</strong> — the corrected values match the
              synthetic demo reference.
            </p>
          ) : null}
          <p className="review-note">
            The recording status on the blockchain is tracked separately from this verification result.
          </p>
          <div className="actions">
            <Link
              to={`/verifications/${submittedResult.newVerificationId}`}
              className="button button--primary"
            >
              View the new result
            </Link>
          </div>
        </section>
      </div>
    );
  }

  if (loading && !verification) {
    return <LoadingState message="Loading review information…" />;
  }

  if (error && !verification) {
    return <ErrorState message={safeMessage(error)} onRetry={() => fetchVerification(verificationId)} />;
  }

  if (!verification) {
    return <ErrorState message="The verification could not be found." onRetry={() => fetchVerification(verificationId)} />;
  }

  const extractedFields = extraction?.extracted_fields ?? {};
  const registryReference: Record<string, string | null> = {};
  for (const cmp of verification.field_comparisons) {
    registryReference[cmp.field] = cmp.registry_value;
  }

  return (
    <div className="page review-page">
      <SyntheticDataBanner />
      <h1>Review this document</h1>
      <p className="page-intro">
        A human review records what you saw in the document. A correction creates a new verification
        using the corrected values — the original OCR reading is never overwritten.
      </p>

      <PipelineTrack current="review" />

      <div className="result-status-row">
        <span className="result-label">Current verification status</span>
        <StatusBadge status={verification.status} />
      </div>

      {error || docError ? (
        <ErrorState message={error ? safeMessage(error) : safeMessage(docError)} onRetry={() => fetchVerification(verificationId)} />
      ) : null}

      <section className="card" aria-label="Reviewer details">
        <h2>Reviewer</h2>
        <label className="form-field">
          <span>Your name</span>
          <input
            type="text"
            value={reviewerRef}
            onChange={(e) => setReviewerRef(e.target.value)}
            placeholder="e.g. Priya (Reviewer)"
            data-testid="reviewer-ref"
          />
        </label>
      </section>

      <section className="card" aria-label="Review action">
        <h2>What do you want to record?</h2>
        <div className="action-options" role="radiogroup" aria-label="Review action">
          {ACTIONS.map((option) => (
            <label
              key={option.value}
              className={`action-option action-option--${option.value.toLowerCase()}${action === option.value ? ' action-option--selected' : ''}`}
            >
              <input
                type="radio"
                name="action"
                value={option.value}
                checked={action === option.value}
                onChange={() => setAction(option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </section>

      {action === 'CORRECT' ? (
        <section className="card" aria-label="Corrected values">
          <h2>Correct a value</h2>
          {(docLoading && !extraction) ? <LoadingState message="Loading extracted values…" /> : null}
          <div className="table-scroll">
            <table className="corrections-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value read by OCR</th>
                  <th>Demo reference</th>
                  <th>Corrected value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(extractedFields).map(([name, field]) => (
                  <tr key={name}>
                    <td>{fieldLabel(name)}</td>
                    <td className="original-value">{field.value ?? 'Not found'}</td>
                    <td className="reference-value">{registryReference[name] ?? '(no value)'}</td>
                    <td>
                      <input
                        type="text"
                        value={corrections[name] ?? field.value ?? ''}
                        onChange={(e) => setCorrections((prev) => ({ ...prev, [name]: e.target.value }))}
                        aria-label={`Corrected value for ${fieldLabel(name)}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            The original OCR value is shown on the left and is never overwritten — the corrected value
            is stored as a separate entry.
          </p>
        </section>
      ) : null}

      <section className="card" aria-label="Comment">
        <h2>Comment</h2>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={4}
          placeholder="Optional note explaining what you saw"
          data-testid="reviewer-comment"
        />
      </section>

      <div className="actions">
        <button
          type="button"
          className={`button ${action === 'ACCEPT' ? 'button--accent' : 'button--primary'}`}
          onClick={handleSubmit}
          disabled={!reviewerRef.trim() || reviewSubmitting}
        >
          {reviewSubmitting ? 'Recording review…' : 'Record review'}
        </button>
        <Link to={`/verifications/${verificationId}`} className="button button--ghost">
          Back to result
        </Link>
      </div>
    </div>
  );
}