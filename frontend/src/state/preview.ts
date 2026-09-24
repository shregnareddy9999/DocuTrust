interface LocalPreview {
  documentId: string;
  url: string;
  size: number;
  kind: 'image' | 'pdf';
}

let preview: LocalPreview | null = null;

/**
 * Remembers the File chosen in this browser session so the document detail screen can show
 * a real preview right after upload. In-memory only — never persisted, never reconstructed.
 */
export function setLocalPreview(documentId: string, file: File): void {
  try {
    if (typeof URL.createObjectURL !== 'function') {
      preview = null;
      return;
    }
    if (preview) URL.revokeObjectURL(preview.url);
    preview = {
      documentId,
      url: URL.createObjectURL(file),
      size: file.size,
      kind: file.type === 'application/pdf' ? 'pdf' : 'image',
    };
  } catch {
    preview = null;
  }
}

export function getLocalPreview(documentId: string): { url: string; size: number; kind: 'image' | 'pdf' } | null {
  if (!preview || preview.documentId !== documentId) return null;
  return { url: preview.url, size: preview.size, kind: preview.kind };
}

export function clearLocalPreview(): void {
  try {
    if (preview && typeof URL.revokeObjectURL === 'function') {
      URL.revokeObjectURL(preview.url);
    }
  } catch {
    // ignore cleanup errors
  }
  preview = null;
}