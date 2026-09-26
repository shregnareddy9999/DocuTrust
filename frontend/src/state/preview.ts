const STORAGE_KEY_PREFIX = 'docutrust.preview';

interface LocalPreview {
  documentId: string;
  url: string;
  size: number;
  kind: 'image' | 'pdf';
}

let preview: LocalPreview | null = null;

/**
 * Remembers the File chosen in this browser session so the document detail screen can show
 * a real preview right after upload. Stored as data URL in localStorage for persistence across reloads.
 */
export function setLocalPreview(documentId: string, file: File): void {
  try {
    // Limit preview to 5MB to avoid localStorage quota issues
    const MAX_SIZE = 5 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      preview = null;
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const kind = file.type === 'application/pdf' ? 'pdf' : 'image';
      preview = { documentId, url: dataUrl, size: file.size, kind };
      try {
        localStorage.setItem(`${STORAGE_KEY_PREFIX}.${documentId}`, JSON.stringify({ url: dataUrl, size: file.size, kind }));
      } catch {
        // localStorage quota exceeded or unavailable
      }
    };
    reader.readAsDataURL(file);
  } catch {
    preview = null;
  }
}

export function getLocalPreview(documentId: string): { url: string; size: number; kind: 'image' | 'pdf' } | null {
  if (preview && preview.documentId === documentId) {
    return { url: preview.url, size: preview.size, kind: preview.kind };
  }
  // Try loading from localStorage
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}.${documentId}`);
    if (raw) {
      const stored = JSON.parse(raw) as { url: string; size: number; kind: 'image' | 'pdf' };
      preview = { documentId, ...stored };
      return stored;
    }
  } catch {
    // ignore parse errors
  }
  return null;
}

export function clearLocalPreview(): void {
  try {
    if (preview && typeof URL.revokeObjectURL === 'function' && preview.url.startsWith('blob:')) {
      URL.revokeObjectURL(preview.url);
    }
  } catch {
    // ignore cleanup errors
  }
  preview = null;
}