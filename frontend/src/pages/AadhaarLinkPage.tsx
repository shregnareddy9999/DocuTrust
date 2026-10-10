import { useMemo, useState } from 'react';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { UploadDropzone } from '../components/UploadDropzone';
import { ApiError } from '../api/client';
import { getAadhaarAssetUrl, uploadAadhaarLinkDocument } from '../api/aadhaarLink';
import type { AadhaarLinkedDocument, AadhaarLinkResponse } from '../types/api';
import { getClientUploadHint, getUploadErrorMessage } from '../utils/messages';

function documentInitial(label: string): string {
  return label
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

function isPdf(row: AadhaarLinkedDocument): boolean {
  return row.asset_mime_type === 'application/pdf';
}

function PreviewPanel({
  row,
  onClose,
}: {
  row: AadhaarLinkedDocument;
  onClose: () => void;
}) {
  const assetUrl = row.asset_ref ? getAadhaarAssetUrl(row.asset_ref) : null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section className="modal aadhaar-preview-modal" role="dialog" aria-modal="true" aria-label="Synthetic sample preview" onClick={(event) => event.stopPropagation()}>
        <div className="modal__header">
          <h3>{row.document_type_label}</h3>
          <button type="button" className="modal__close" aria-label="Close preview" onClick={onClose}>
            x
          </button>
        </div>
        <div className="modal__body">
          {assetUrl ? (
            isPdf(row) ? (
              <iframe className="aadhaar-preview-frame" title={row.document_type_label} src={assetUrl} />
            ) : (
              <img className="aadhaar-preview-image" src={assetUrl} alt={`${row.document_type_label} synthetic sample`} />
            )
          ) : (
            <ErrorState message="This synthetic record does not have a local sample asset yet." />
          )}
        </div>
      </section>
    </div>
  );
}

function CitizenSummary({ result }: { result: AadhaarLinkResponse }) {
  return (
    <section className="card aadhaar-citizen-card" aria-label="Synthetic citizen summary">
      <div className="aadhaar-citizen-top">
        <div className="aadhaar-citizen-main">
          <div className="aadhaar-avatar" aria-hidden="true">ID</div>
          <div>
            <div className="aadhaar-name-row">
              <h2>{result.citizen.demo_name}</h2>
              <span className="aadhaar-pill">Matched synthetic demo registry</span>
            </div>
            <p>{result.citizen.citizen_ref} linked through {result.citizen.aadhaar_ref}</p>
          </div>
        </div>
        <div className="aadhaar-id-chips">
          <div className="aadhaar-id-chip">
            <span>Masked demo Aadhaar</span>
            <strong>{result.citizen.masked_aadhaar}</strong>
          </div>
          {result.citizen.demo_mobile_placeholder ? (
            <div className="aadhaar-id-chip">
              <span>Synthetic demo mobile</span>
              <strong>{result.citizen.demo_mobile_placeholder}</strong>
            </div>
          ) : null}
        </div>
      </div>

      <dl className="aadhaar-summary-grid">
        <div>
          <dt>Linked credentials</dt>
          <dd>{result.summary.linked_record_count} Records</dd>
        </div>
        <div>
          <dt>Demo seed</dt>
          <dd>{result.summary.blockchain_seed}</dd>
        </div>
        <div>
          <dt>Last sync note</dt>
          <dd>{result.summary.last_sync_label}</dd>
        </div>
      </dl>
    </section>
  );
}

function LinkedDocumentRow({
  row,
  onPreview,
}: {
  row: AadhaarLinkedDocument;
  onPreview: (row: AadhaarLinkedDocument) => void;
}) {
  const content = (
    <>
      <span className="aadhaar-doc-icon" aria-hidden="true">{documentInitial(row.document_type_label)}</span>
      <span className="aadhaar-doc-main">
        <span className="aadhaar-doc-title">
          {row.document_type_label}
          <span className="aadhaar-doc-badge">{row.status_label}</span>
        </span>
        <span className="aadhaar-doc-source">{row.issuer_label}</span>
        <span className="aadhaar-doc-meta">
          {row.display_value}
          {row.demo_mobile_placeholder ? ` - synthetic demo mobile: ${row.demo_mobile_placeholder}` : ''}
        </span>
      </span>
      {row.asset_ref ? <span className="aadhaar-doc-action">Preview</span> : <span className="aadhaar-doc-static">No sample document</span>}
    </>
  );

  if (!row.asset_ref) {
    return <div className="aadhaar-doc-row aadhaar-doc-row--static">{content}</div>;
  }

  return (
    <button type="button" className="aadhaar-doc-row" onClick={() => onPreview(row)}>
      {content}
    </button>
  );
}

export function AadhaarLinkPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<AadhaarLinkResponse | null>(null);
  const [preview, setPreview] = useState<AadhaarLinkedDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedLabel = useMemo(() => {
    if (!selectedFile) return null;
    return `${selectedFile.name} (${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)`;
  }, [selectedFile]);

  async function handleUpload() {
    if (!selectedFile || loading) return;
    const hint = getClientUploadHint(selectedFile);
    if (hint) {
      setError(hint);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await uploadAadhaarLinkDocument(selectedFile);
      setResult(response);
    } catch (uploadError) {
      if (
        uploadError instanceof ApiError &&
        (uploadError.code === 'AADHAAR_DEMO_CARD_REQUIRED' ||
          uploadError.code === 'AADHAAR_DEMO_REFERENCE_NOT_FOUND')
      ) {
        setError(uploadError.message);
      } else {
        setError(getUploadErrorMessage(uploadError));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page aadhaar-page">
      <h1>Aadhaar Link & Demo Records</h1>
      <p className="page-intro">
        Upload a synthetic Aadhaar demo file to discover linked synthetic records. This page does not contact UIDAI or any real issuer.
      </p>

      <section className="card aadhaar-upload-card" aria-label="Upload Aadhaar demo document" aria-busy={loading}>
        <h2>Upload Aadhaar Demo Card</h2>
        <UploadDropzone
          disabled={loading}
          onFileSelected={(file) => {
            setSelectedFile(file);
            setError(null);
          }}
        />
        {selectedLabel ? <p className="file-selected">Selected file: <strong>{selectedLabel}</strong></p> : null}
        {error ? <ErrorState message={error} /> : null}
        <div className="actions aadhaar-upload-actions">
          <button type="button" className="button button--primary" disabled={!selectedFile || loading} onClick={handleUpload}>
            {loading ? 'Finding linked records...' : 'Upload & Find Links'}
          </button>
        </div>
        {loading ? <LoadingState message="Reading the synthetic demo link..." /> : null}
      </section>

      {result ? (
        <>
          <CitizenSummary result={result} />
          <section className="card aadhaar-documents-card" aria-label="Linked synthetic records">
            <div className="aadhaar-section-header">
              <div>
                <h2>Linked Synthetic Documents</h2>
                <p>Records discovered through the synthetic Aadhaar demo link.</p>
              </div>
              <button type="button" className="button button--secondary" disabled={loading} onClick={handleUpload}>
                Refresh Links
              </button>
            </div>
            <div className="aadhaar-doc-list">
              {result.linked_documents.length > 0 ? (
                result.linked_documents.map((row) => (
                  <LinkedDocumentRow key={row.id} row={row} onPreview={setPreview} />
                ))
              ) : (
                <div className="aadhaar-doc-row aadhaar-doc-row--static">
                  <span className="aadhaar-doc-main">
                    <span className="aadhaar-doc-title">No linked synthetic records found</span>
                    <span className="aadhaar-doc-meta">This synthetic Aadhaar reference exists, but Supabase has no linked records for it.</span>
                  </span>
                </div>
              )}
            </div>
          </section>
        </>
      ) : null}

      {preview ? <PreviewPanel row={preview} onClose={() => setPreview(null)} /> : null}
    </div>
  );
}
