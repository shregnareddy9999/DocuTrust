import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  generateAcademicSummary,
  type AcademicSummaryResponse,
} from '../api/academicSummary';

import { uploadDocument } from '../api/documents';

import { ApiError } from '../api/client';

import { SyntheticDataBanner } from '../components/SyntheticDataBanner';

import { LoadingState } from '../components/LoadingState';

import { addRecentDocument } from '../state/recentDocuments';

const MAX_FILES = 5;

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Could not generate the academic summary.';
}

export function AcademicSummaryPage() {
  const [files, setFiles] = useState<File[]>([]);

  const [summary, setSummary] =
    useState<AcademicSummaryResponse | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [loading, setLoading] = useState(false);

  const canGenerate =
    files.length > 0 &&
    files.length <= MAX_FILES &&
    !loading;

  const totalSizeMb = useMemo(
    () =>
      files.reduce(
        (total, file) => total + file.size,
        0,
      ) /
      (1024 * 1024),
    [files],
  );

  function handleFiles(
    selected: FileList | null,
  ) {
    if (!selected) {
      return;
    }

    setError(null);
    setSummary(null);

    const next = Array.from(selected).slice(
      0,
      MAX_FILES,
    );

    setFiles(next);

    if (selected.length > MAX_FILES) {
      setError(
        `Please select at most ${MAX_FILES} academic documents.`,
      );
    }
  }

  async function handleGenerate() {
    if (!canGenerate) {
      return;
    }

    setLoading(true);
    setError(null);
    setSummary(null);

    try {
      const documentIds: string[] = [];

      for (const file of files) {
        const uploaded = await uploadDocument(
          file,
          'academic_certificate',
        );

        documentIds.push(
          uploaded.document_id,
        );

        addRecentDocument(
          uploaded.document_id,
        );
      }

      const result =
        await generateAcademicSummary({
          document_ids: documentIds,
        });

      setSummary(result);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setFiles([]);
    setSummary(null);
    setError(null);
  }

  return (
    <div className="page academic-summary-page">
      <SyntheticDataBanner />

      <h1>AI Academic Summary</h1>

      <p className="page-intro">
        Upload up to five synthetic academic
        marksheets. DocuTrust reads the documents
        with the existing OCR pipeline and uses
        the local AI model to create one concise
        summary.
      </p>

      <section className="card">
        <h2>1. Select academic documents</h2>

        <label className="summary-file-picker">
          <span className="button button--secondary">
            Choose marksheets
          </span>

          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            multiple
            onChange={(event) =>
              handleFiles(
                event.target.files,
              )
            }
            disabled={loading}
          />
        </label>

        <p className="note">
          PDF, PNG, or JPEG. Maximum 5 documents
          in one summary request.
        </p>

        {files.length > 0 ? (
          <ul
            className="summary-file-list"
            aria-label="Selected academic documents"
          >
            {files.map((file) => (
              <li
                key={`${file.name}-${file.lastModified}`}
              >
                <span>{file.name}</span>

                <span>
                  {(file.size / 1024).toFixed(0)} KB
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {error ? (
          <p
            className="form-error"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <div className="actions">
          <button
            type="button"
            className="button button--primary"
            disabled={!canGenerate}
            onClick={handleGenerate}
          >
            {loading
              ? 'Reading documents and generating…'
              : 'Generate AI Summary'}
          </button>

          {files.length > 0 && !loading ? (
            <button
              type="button"
              className="button button--ghost"
              onClick={handleClear}
            >
              Clear
            </button>
          ) : null}
        </div>

        {files.length > 0 ? (
          <p className="note">
            Selected size:{' '}
            {totalSizeMb.toFixed(2)} MB
          </p>
        ) : null}
      </section>

      {loading ? (
        <LoadingState
          message="OCR is reading the documents and the local AI model is preparing the summary…"
        />
      ) : null}

      {summary ? (
        <section
          className="card academic-summary-result"
          aria-live="polite"
        >
          <div className="academic-summary-result__header">
            <div>
              <h2>Academic Summary</h2>

              <p className="note">
                Generated from{' '}
                {summary.documents_analyzed}{' '}
                document(s) using{' '}
                {summary.model}.
              </p>
            </div>

            <span className="summary-ai-badge">
              LOCAL AI
            </span>
          </div>

          <p className="academic-summary-result__text">
            {summary.summary}
          </p>

          <p className="note">
            This is an AI-generated summary of
            the supplied OCR text. It does not
            establish document authenticity or
            government verification.
          </p>

          <div className="actions">
            <Link
              to="/documents"
              className="button button--secondary"
            >
              View Documents
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}
