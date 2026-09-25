import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../state/useDocument';
import { useVerification } from '../state/useVerification';
import { UploadDropzone } from '../components/UploadDropzone';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { ProcessingSteps, type ProcessingStep } from '../components/ProcessingSteps';
import { PipelineTrack } from '../components/PipelineTrack';
import { getUploadErrorMessage, getVerifyErrorMessage, safeMessage } from '../utils/messages';
import { setLocalPreview } from '../state/preview';
import { addRecentDocument, getRecentDocumentIds } from '../state/recentDocuments';
import { getDocument } from '../api/documents';
import { pathAfterVerification } from '../utils/reviewNavigation';

type Stage = 'idle' | 'uploading' | 'verifying' | 'preparing';

function stepsForStage(stage: Stage): ProcessingStep[] {
  switch (stage) {
    case 'uploading':
      return [
        { label: 'Document uploaded', state: 'active' },
        { label: 'Reading and comparing', state: 'pending' },
        { label: 'Preparing result', state: 'pending' },
      ];
    case 'verifying':
      return [
        { label: 'Document uploaded', state: 'done' },
        { label: 'Reading and comparing', state: 'active' },
        { label: 'Preparing result', state: 'pending' },
      ];
    case 'preparing':
      return [
        { label: 'Document uploaded', state: 'done' },
        { label: 'Reading and comparing', state: 'done' },
        { label: 'Preparing result', state: 'active' },
      ];
    default:
      return [];
  }
}

export function UploadPage() {
  const navigate = useNavigate();
  const { documentTypes, loading, error, fetchDocumentTypes, upload, clearError } = useDocument();
  const { runVerification, clearError: clearVerifyError } = useVerification();
  const [category, setCategory] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>('idle');
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [isDuplicate, setIsDuplicate] = useState(false);

  useEffect(() => {
    fetchDocumentTypes();
  }, [fetchDocumentTypes]);

  const processing = stage !== 'idle';

  async function checkDuplicate(fileName: string): Promise<boolean> {
    const recentIds = getRecentDocumentIds();
    for (const id of recentIds) {
      try {
        const doc = await getDocument(id);
        if (doc.original_filename === fileName) {
          return true;
        }
      } catch {
        // ignore errors
      }
    }
    return false;
  }

  async function handleFileSelected(file: File) {
    if (processing) return;
    clearError();
    clearVerifyError();
    setUploadError(null);
    setDuplicateWarning(null);
    setIsDuplicate(false);
    setSelectedFile(file);

    // Check for duplicate file name in history
    const duplicate = await checkDuplicate(file.name);
    if (duplicate) {
      setDuplicateWarning(`Document "${file.name}" is already uploaded.`);
      setIsDuplicate(true);
    }
  }

  async function handleVerify() {
    if (!selectedFile || !category || processing) return;
    if (isDuplicate) {
      setDuplicateWarning(`Document "${selectedFile.name}" is already uploaded. Please choose a different file.`);
      return;
    }
    setUploadError(null);
    setDuplicateWarning(null);
    setStage('uploading');
    try {
      const uploaded = await upload(selectedFile, category);
      setLocalPreview(uploaded.document_id, selectedFile);
      addRecentDocument(uploaded.document_id);
      setStage('verifying');
      try {
        const result = await runVerification(uploaded.document_id);
        setStage('preparing');
        navigate(pathAfterVerification(result.verification_id, result.status), {
          state: { status: result.status },
        });
      } catch (verifyErr) {
        setStage('idle');
        setUploadError(getVerifyErrorMessage(verifyErr));
      }
    } catch (uploadErr) {
      setStage('idle');
      setUploadError(getUploadErrorMessage(uploadErr));
    }
  }

  if (loading && documentTypes.length === 0) {
    return <LoadingState message="Loading document categories…" />;
  }

  if (documentTypes.length === 0 && !loading && !error) {
    return (
      <EmptyState
        title="No document categories available"
        message="The server did not return any document categories. Try again later."
      />
    );
  }

  if (error && documentTypes.length === 0) {
    return <ErrorState message={safeMessage(error)} onRetry={() => fetchDocumentTypes()} />;
  }

  return (
    <div className="page upload-page">
      <h1>Verify a document</h1>
      <p className="page-intro">
        Choose a document category, then upload a file. The document is read by OCR and compared
        against the synthetic demo registry right after upload — this does not evaluate real
        documents.
      </p>

      <PipelineTrack current={stage === 'idle' ? 'upload' : 'compare'} />

      <section className="card" aria-label="Document category" aria-busy={processing}>
        <h2>1. Choose a category</h2>
        <div className="category-list" role="radiogroup" aria-label="Document categories">
          {documentTypes.map((type) => (
            <label key={type.category} className="category-option">
              <input
                type="radio"
                name="category"
                value={type.category}
                checked={category === type.category}
                onChange={() => setCategory(type.category)}
                disabled={processing}
              />
              <span>{type.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="card" aria-label="File upload" aria-busy={processing}>
        <h2>2. Upload the document</h2>
        <UploadDropzone onFileSelected={handleFileSelected} disabled={processing} />
        {selectedFile ? (
          <p className="file-selected">
            Selected file: <strong>{selectedFile.name}</strong>{' '}
            ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
          </p>
        ) : null}
        {duplicateWarning ? (
          <p className="form-error" role="alert">
            {duplicateWarning}
          </p>
        ) : null}
        {uploadError ? (
          <p className="form-error" role="alert">
            {uploadError}
          </p>
        ) : null}
        <div className="actions">
          <button
            type="button"
            className="button button--primary"
            disabled={!selectedFile || !category || processing || isDuplicate}
            onClick={handleVerify}
          >
            {stage === 'verifying'
              ? 'Reading and comparing…'
              : stage === 'preparing'
                ? 'Preparing result…'
                : 'Upload and verify'}
          </button>
        </div>
        {processing ? <ProcessingSteps steps={stepsForStage(stage)} /> : null}
      </section>
    </div>
  );
}