import { useRef, useState } from 'react';

interface UploadDropzoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED_EXTENSIONS = ['image/jpeg', 'image/png', 'application/pdf'];

export function UploadDropzone({ onFileSelected, disabled = false }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFile(file: File | undefined | null) {
    if (file) {
      onFileSelected(file);
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const file = event.dataTransfer.files?.[0];
    handleFile(file);
  }

  return (
    <div
      className={isDragging ? 'dropzone dropzone--dragging' : 'dropzone'}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (disabled) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(',')}
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0])}
        data-testid="file-input"
      />
      <p className="dropzone-title">Drag and drop a document here, or click to choose a file</p>
      <p className="dropzone-hint">Accepted formats: JPEG, PNG, PDF. Maximum size: 10 MB.</p>
    </div>
  );
}