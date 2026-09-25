import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocument } from '../state/useDocument';
import { useVerification } from '../state/useVerification';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { ProcessingSteps, type ProcessingStep } from '../components/ProcessingSteps';
import { PipelineTrack } from '../components/PipelineTrack';
import { getLocalPreview } from '../state/preview';
import { addRecentDocument } from '../state/recentDocuments';
import { pathAfterVerification } from '../utils/reviewNavigation';
import { safeMessage, translateWarning, getVerifyErrorMessage } from '../utils/messages';
import {
  describeOcrConfidence,
  formatOcrConfidence,
  ocrConfidenceMessage,
} from '../utils/confidence';
import type { DocumentType } from '../types/api';

function fieldLabel(fieldName: string, fields: DocumentType[]): string {
  for (const type of fields) {
    const match = type.fields.find((f) => f.name === fieldName);
    if (match) return match.label;
  }
  return fieldName;
}

type VerifyStage = 'idle' | 'verifying' | 'preparing';

function stepsForStage(stage: VerifyStage): ProcessingStep[] {
  if (stage === 'idle') return [];
  return [
    { label: 'Document uploaded', state: 'done' },
    { label: 'Reading and comparing', state: stage === 'verifying' ? 'active' : 'done' },
    { label: 'Preparing result', state: stage === 'preparing' ? 'active' : 'pending' },
  ];
}

function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function DocumentDetailPage() {
  const { documentId = '' } = useParams();
  const navigate = useNavigate();
  const { document, extraction, documentTypes, loading, error, fetchDocument, fetchExtraction, fetchDocumentTypes, clearError } =
    useDocument();
  const { runVerification, error: verifyError, clearError: clearVerifyError } = useVerification();

  const [verifyStage, setVerifyStage] = useState<VerifyStage>('idle');

  useEffect(() => {
    fetchDocumentTypes();
    fetchDocument(documentId);
    fetchExtraction(documentId);
    if (documentId) addRecentDocument(documentId);
  }, [documentId, fetchDocument, fetchExtraction, fetchDocumentTypes]);

  function reload() {
    clearError();
    clearVerifyError();
    fetchDocument(documentId);
    fetchExtraction(documentId);
  }

  async function handleRunComparison() {
    if (verifyStage !== 'idle') return;
    setVerifyStage('verifying');
    clearVerifyError();
    try {
      const result = await runVerification(documentId);
      setVerifyStage('preparing');
      navigate(pathAfterVerification(result.verification_id, result.status), {
        state: { status: result.status },
      });
    } catch {
      setVerifyStage('idle');
    }
  }

  if (loading && !document && !extraction) {
    return <LoadingState message="Loading…" />;
  }

  const displayedError = verifyError ? getVerifyErrorMessage(verifyError) : error ? safeMessage(error) : null;
  if (displayedError) {
    return (
      <ErrorState
        message={displayedError}
        onRetry={verifyError ? handleRunComparison : reload}
      />
    );
  }

  if (!document) {
    return <ErrorState message="Document not found" onRetry={reload} />;
  }

  const preview = getLocalPreview(documentId);

  return (
    <div className="page document-detail-page">
      <h1>Extracted document details</h1>
      <p className="page-intro">
        These values were read from the uploaded file by OCR. Confidence describes how reliably the
        characters were read — it is not a statement about the document's authenticity.
      </p>

      <PipelineTrack current={verifyStage === 'idle' ? 'extract' : 'compare'} />

      {preview ? (
        <section className="card" aria-label="Uploaded document">
          <h2>Uploaded document</h2>
          {preview.kind === 'pdf' ? (
            <iframe className="preview-frame" src={preview.url} title="Document preview" />
          ) : (
            <img className="preview-image" src={preview.url} alt="Uploaded document" />
          )}
          <div className="receipt-row">
            <span className="receipt-label">File name</span>
            <span className="receipt-value">{document.original_filename}</span>
          </div>
          <div className="receipt-row">
            <span className="receipt-label">Size</span>
            <span className="receipt-value">{formatSize(preview.size)}</span>
          </div>
        </section>
      ) : (
        <p className="note">Document preview not available</p>
      )}

      {!extraction ? (
        <EmptyState
          title="No extraction available"
          message="The OCR step did not produce a result for this document."
        />
      ) : extraction.status === 'FAILED' ? (
        <div className="card">
          <h2>Text extraction could not be completed</h2>
          {extraction.warnings.length > 0 ? (
            <ul className="warning-list">
              {extraction.warnings.map((w) => (
                <li key={w}>{translateWarning(w)}</li>
              ))}
            </ul>
          ) : (
            <p>A technical error prevented the document from being read.</p>
          )}
        </div>
      ) : (
        <section className="card" aria-label="Extracted fields">
          <h2>Extracted fields</h2>
          {extraction.warnings.length > 0 ? (
            <ul className="warning-list">
              {extraction.warnings.map((w) => (
                <li key={w}>{translateWarning(w)}</li>
              ))}
            </ul>
          ) : null}
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
                {Object.entries(extraction.extracted_fields).map(([name, field]) => {
                  const summary = describeOcrConfidence(field.confidence);
                  const lowConfidence = summary.state === 'low';
                  return (
                    <tr key={name} className={lowConfidence ? 'row--low-confidence' : undefined}>
                      <td>{fieldLabel(name, documentTypes)}</td>
                      <td className={field.value === null ? 'field-not-found' : undefined}>
                        {field.value === null ? 'Not found' : field.value}
                      </td>
                      <td>
                        {summary.state === 'none' ? (
                          '—'
                        ) : (
                          <>
                            {lowConfidence ? (
                              <span className="tag tag--warning">{ocrConfidenceMessage(field.confidence)}</span>
                            ) : (
                              <span>{ocrConfidenceMessage(field.confidence)}</span>
                            )}
                            <span className="confidence-note">
                              {' '}OCR confidence: {formatOcrConfidence(field.confidence)}
                            </span>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <div className="actions">
        <button
          type="button"
          className="button button--primary"
          onClick={handleRunComparison}
          disabled={verifyStage !== 'idle'}
        >
          {verifyStage === 'verifying' ? 'Reading and comparing…' : 'Run comparison'}
        </button>
        <button
          type="button"
          className="button button--secondary"
          onClick={reload}
          disabled={verifyStage !== 'idle'}
        >
          Reload
        </button>
      </div>

      {verifyStage !== 'idle' ? <ProcessingSteps steps={stepsForStage(verifyStage)} /> : null}
    </div>
  );
}