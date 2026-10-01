import { useEffect, useMemo } from 'react';
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';

import {
  ArrowRightIcon,
  DocumentsIcon,
} from '../components/icons';

interface AcademicSummaryDocument {
  documentId: string;
  fileName: string;
  size: number;
  file: File;
}

interface AcademicSummaryPreviewLocationState {
  document?: AcademicSummaryDocument;
}

export function AcademicSummaryDocumentPreviewPage() {
  const { documentId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const state =
    location.state as AcademicSummaryPreviewLocationState | null;

  const document = state?.document;
  const previewFile = document?.file;

  const previewUrl = useMemo(() => {
    if (!previewFile) {
      return null;
    }

    return URL.createObjectURL(previewFile);
  }, [previewFile]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  if (
    !document ||
    document.documentId !== documentId ||
    !document.file
  ) {
    return (
      <main className="page academic-preview-page">
        <section className="academic-preview-missing">
          <DocumentsIcon />

          <h1>Document Preview Unavailable</h1>

          <p>
            This preview is available during the current upload
            session. Please return to Academic Summary and select
            the document again.
          </p>

          <Link
            to="/academic-summary"
            className="button button--primary"
          >
            Back to Academic Summary
            <ArrowRightIcon />
          </Link>
        </section>
      </main>
    );
  }

  const isPdf =
    document.file.type === 'application/pdf' ||
    document.fileName.toLowerCase().endsWith('.pdf');

  return (
    <main className="page academic-preview-page">
      <section className="page-header academic-preview-header">
        <div>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => navigate(-1)}
          >
            ← Back
          </button>

          <p className="eyebrow">Academic Document</p>

          <h1>{document.fileName}</h1>

          <p className="page-description">
            Previewing the document uploaded for AI Academic
            Summary.
          </p>
        </div>
      </section>

      <section className="academic-preview-card">
        <div className="academic-preview-toolbar">
          <div>
            <strong>{document.fileName}</strong>

            <span>
              {(document.size / (1024 * 1024)).toFixed(2)} MB
            </span>
          </div>

          <Link
            to="/academic-summary"
            className="button button--secondary"
          >
            Back to Summary
          </Link>
        </div>

        <div className="academic-preview-viewer">
          {previewUrl && isPdf && (
            <iframe
              src={previewUrl}
              title={`Preview of ${document.fileName}`}
              className="academic-preview-pdf"
            />
          )}

          {previewUrl && !isPdf && (
            <div className="academic-preview-image-wrapper">
              <img
                src={previewUrl}
                alt={`Preview of ${document.fileName}`}
                className="academic-preview-image"
              />
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
