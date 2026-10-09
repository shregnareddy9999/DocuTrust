import { useEffect, useRef, useState } from 'react';
import { generateAcademicSummary } from '../api/academicSummary';
import { deleteDocument, getDocument, getDocumentFile, uploadDocument } from '../api/documents';
import { ApiError } from '../api/client';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { DocumentsIcon, TrashIcon } from '../components/icons';
import { LoadingState } from '../components/LoadingState';
import { getLocalPreview, setLocalPreview } from '../state/preview';
import { getClientUploadHint, getUploadErrorMessage } from '../utils/messages';
import type { AcademicSummaryResponse, Document } from '../types/api';

type UploadedSummaryDocument = {
  documentId: string;
  fileName: string;
  uploadedAt: string;
  file: File;
};

type PreviewState = {
  documentId: string;
  fileName: string;
  uploadedAt: string;
  mimeType: string;
  url: string;
  kind: 'image' | 'pdf' | 'unsupported';
  size: number | null;
};

const ACCEPTED_UPLOAD_TYPES = 'image/jpeg,image/png,application/pdf';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'AI_SUMMARY_UNAVAILABLE') {
      return 'Could not reach local Ollama. Start Ollama with llama3.2:latest, then try again.';
    }
    return error.message;
  }
  return 'Could not generate the academic summary.';
}

function toUploadedDocument(document: Document, file: File): UploadedSummaryDocument {
  return {
    documentId: document.document_id,
    fileName: document.original_filename,
    uploadedAt: document.uploaded_at,
    file,
  };
}

export function AcademicSummaryPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedSummaryDocument[]>([]);
  const [summary, setSummary] = useState<AcademicSummaryResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (preview?.url.startsWith('blob:')) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [preview]);

  function handleFilesSelected(files: FileList | null): void {
    setUploadError(null);
    setSummary(null);
    setSelectedFiles(files ? Array.from(files) : []);
  }

  async function handleUpload(): Promise<void> {
    if (selectedFiles.length === 0 || uploading) return;

    const firstClientError = selectedFiles.map(getClientUploadHint).find(Boolean);
    if (firstClientError) {
      setUploadError(firstClientError);
      return;
    }

    setUploading(true);
    setUploadError(null);
    setDeleteError(null);
    try {
      const created: UploadedSummaryDocument[] = [];
      for (const file of selectedFiles) {
        const uploaded = await uploadDocument(file, 'academic_certificate');
        setLocalPreview(uploaded.document_id, file);
        const document = await getDocument(uploaded.document_id);
        created.push(toUploadedDocument(document, file));
      }
      setUploadedDocs((current) => [...created, ...current]);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (caught) {
      setUploadError(getUploadErrorMessage(caught));
    } finally {
      setUploading(false);
    }
  }

  async function onSubmit(): Promise<void> {
    if (submittingRef.current) return;
    if (uploadedDocs.length === 0) {
      setSubmitError('Upload at least one academic document.');
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await generateAcademicSummary(uploadedDocs.map((doc) => doc.documentId));
      setSummary(result);
    } catch (caught) {
      setSummary(null);
      setSubmitError(errorMessage(caught));
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  async function openPreview(row: UploadedSummaryDocument): Promise<void> {
    if (preview?.url.startsWith('blob:')) {
      URL.revokeObjectURL(preview.url);
    }
    setPreview(null);
    setPreviewError(null);
    setPreviewLoadingId(row.documentId);

    const localPreview = getLocalPreview(row.documentId);
    if (localPreview) {
      setPreview({
        documentId: row.documentId,
        fileName: row.fileName,
        uploadedAt: row.uploadedAt,
        mimeType: localPreview.kind === 'pdf' ? 'application/pdf' : 'image/*',
        url: localPreview.url,
        kind: localPreview.kind,
        size: localPreview.size,
      });
      setPreviewLoadingId(null);
      return;
    }

    try {
      const blob = await getDocumentFile(row.documentId);
      const url = URL.createObjectURL(blob);
      const isPdf = blob.type === 'application/pdf';
      const isImage = blob.type.startsWith('image/');
      setPreview({
        documentId: row.documentId,
        fileName: row.fileName,
        uploadedAt: row.uploadedAt,
        mimeType: blob.type || 'application/octet-stream',
        url,
        kind: isPdf ? 'pdf' : isImage ? 'image' : 'unsupported',
        size: blob.size,
      });
    } catch (caught) {
      setPreviewError(errorMessage(caught));
    } finally {
      setPreviewLoadingId(null);
    }
  }

  async function handleDelete(row: UploadedSummaryDocument): Promise<void> {
    if (deletingId) return;
    const confirmed = window.confirm(`Delete "${row.fileName}" from this summary upload list?`);
    if (!confirmed) return;

    setDeletingId(row.documentId);
    setDeleteError(null);
    try {
      await deleteDocument(row.documentId);
      setUploadedDocs((current) => current.filter((doc) => doc.documentId !== row.documentId));
      if (preview?.documentId === row.documentId) {
        closePreview();
      }
      setSummary(null);
    } catch (caught) {
      setDeleteError(errorMessage(caught));
    } finally {
      setDeletingId(null);
    }
  }

  function closePreview(): void {
    if (preview?.url.startsWith('blob:')) {
      URL.revokeObjectURL(preview.url);
    }
    setPreview(null);
    setPreviewError(null);
  }

  return (
    <div className="page academic-summary-page">
      <h1>AI Summary</h1>
      <p className="page-intro">
        Upload one or more academic documents here, then generate a summary from only those files.
      </p>

      <section className="card" aria-label="Upload academic documents" aria-busy={uploading}>
        <h2>Upload Academic Documents</h2>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_UPLOAD_TYPES}
          multiple
          disabled={uploading || submitting}
          onChange={(event) => handleFilesSelected(event.target.files)}
          data-testid="summary-file-input"
        />
        <p className="dropzone-hint">Accepted formats: JPEG, PNG, PDF. Maximum size: 10 MB each.</p>
        {selectedFiles.length > 0 ? (
          <ul className="academic-summary-file-list">
            {selectedFiles.map((file) => (
              <li key={`${file.name}-${file.size}`}>
                {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </li>
            ))}
          </ul>
        ) : null}
        {uploadError ? (
          <p className="form-error" role="alert">
            {uploadError}
          </p>
        ) : null}
        <div className="academic-summary-actions">
          <button
            type="button"
            className="button button--primary"
            onClick={() => void handleUpload()}
            disabled={selectedFiles.length === 0 || uploading || submitting}
          >
            {uploading ? 'Uploading...' : 'Upload Documents'}
          </button>
        </div>
        {uploading ? <LoadingState message="Uploading documents..." /> : null}
      </section>

      {uploadedDocs.length === 0 ? (
        <EmptyState
          icon={<DocumentsIcon />}
          title={<strong>No documents uploaded here yet</strong>}
          message="Choose one or more academic documents above to start a summary."
        />
      ) : (
        <>
          <section className="card" aria-label="Uploaded summary documents">
            <div className="table-scroll">
              <table className="documents-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedDocs.map((row) => (
                    <tr key={row.documentId}>
                      <td className="doc-name">
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => void openPreview(row)}
                          disabled={previewLoadingId === row.documentId}
                        >
                          {previewLoadingId === row.documentId ? 'Opening...' : row.fileName}
                        </button>
                      </td>
                      <td>{new Date(row.uploadedAt).toLocaleDateString()}</td>
                      <td>
                        <button
                          type="button"
                          className="icon-button"
                          aria-label={`Delete ${row.fileName}`}
                          onClick={() => void handleDelete(row)}
                          disabled={deletingId !== null}
                          title="Delete document"
                        >
                          <TrashIcon />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {deleteError ? <ErrorState message={deleteError} /> : null}
            <div className="academic-summary-actions">
              <button
                type="button"
                className="button button--primary"
                onClick={() => void onSubmit()}
                disabled={submitting || uploading}
              >
                {submitting ? 'Generating...' : 'Generate AI Summary'}
              </button>
            </div>
          </section>

          <p className="academic-summary-note">
            The summary uses only OCR text from the documents uploaded on this page.
          </p>

          {submitError ? <ErrorState message={submitError} /> : null}

          {submitting ? <LoadingState message="Generating AI summary..." /> : null}

          {summary ? (
            <section className="card academic-summary-result" aria-label="AI academic summary result">
              <h2>AI Summary</h2>
              <p>{summary.summary}</p>
              <dl className="academic-summary-meta">
                <div>
                  <dt>Documents Analyzed</dt>
                  <dd>{summary.documents_analyzed}</dd>
                </div>
                <div>
                  <dt>Model Used</dt>
                  <dd>{summary.model}</dd>
                </div>
              </dl>
            </section>
          ) : null}

          {preview ? (
            <section className="card academic-summary-preview" aria-label="Document preview">
              <div className="academic-summary-preview__header">
                <div>
                  <h2>{preview.fileName}</h2>
                  <p className="page-intro">
                    Uploaded {new Date(preview.uploadedAt).toLocaleString()} - {preview.mimeType}
                  </p>
                </div>
                <button type="button" className="button button--secondary" onClick={closePreview}>
                  Close Preview
                </button>
              </div>
              {preview.kind === 'image' ? (
                <img className="preview-image" src={preview.url} alt={preview.fileName} />
              ) : preview.kind === 'pdf' ? (
                <iframe className="preview-frame" src={preview.url} title={preview.fileName} />
              ) : (
                <p className="note">Preview is not available for this file type.</p>
              )}
              <a className="button button--secondary" href={preview.url} download={preview.fileName}>
                Download Document
              </a>
            </section>
          ) : null}

          {previewError ? <ErrorState message={previewError} /> : null}
        </>
      )}
    </div>
  );
}
