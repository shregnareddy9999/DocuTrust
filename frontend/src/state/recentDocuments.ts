import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { getDocument } from '../api/documents';
import { getDocumentTypes } from '../api/documentTypes';
import { getBlockchain, getVerification, getVerificationHistory } from '../api/verifications';
import type {
  BlockchainStatus,
  VerificationStatus,
} from '../types/api';

/**
 * Client-side list of documents opened in this browser session.
 *
 * The API has no list endpoints, so the shell screens are built over this module:
 * it stores document IDs only (localStorage, best-effort) and hydrates each row
 * with the EXISTING document/verification/blockchain endpoints. A real list
 * endpoint can be swapped in behind the same surface later.
 */
const STORAGE_KEY = 'docutrust.recentDocuments';
const MAX_DOCS = 20;

function readIds(): string[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((entry): entry is string => typeof entry === 'string');
  } catch {
    return [];
  }
}

let ids: string[] = readIds();
let snapshot: string[] = ids.slice();

function writeIds(): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // storage unavailable; the in-memory list still works
  }
}

const listeners = new Set<() => void>();

function emit(): void {
  snapshot = ids.slice();
  for (const listener of listeners) listener();
}

export function addRecentDocument(documentId: string): void {
  ids = [documentId, ...ids.filter((id) => id !== documentId)].slice(0, MAX_DOCS);
  writeIds();
  emit();
}

export function getRecentDocumentIds(): string[] {
  return snapshot;
}

export function clearRecentDocuments(): void {
  ids = [];
  writeIds();
  emit();
}

export function subscribeRecentDocuments(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useRecentDocumentIds(): string[] {
  return useSyncExternalStore(subscribeRecentDocuments, () => snapshot, () => []);
}

export interface RecentDocumentHistoryRow {
  verificationId: string;
  status: VerificationStatus;
  isCurrent: boolean;
  createdAt: string;
  reviewedBy: string | null;
}

export interface RecentDocumentRow {
  documentId: string;
  fileName: string;
  categoryLabel: string;
  uploadedAt: string;
  currentVerificationId: string | null;
  currentStatus: VerificationStatus | null;
  blockchainStatus: BlockchainStatus | null;
  history: RecentDocumentHistoryRow[];
}

export interface RecentDocumentsState {
  loading: boolean;
  error: string | null;
  rows: RecentDocumentRow[];
  reload: () => void;
}

async function hydrateRow(
  documentId: string,
  categoryLabels: Record<string, string>
): Promise<RecentDocumentRow> {
  const document = await getDocument(documentId);
  const historyResponse = await getVerificationHistory(documentId);
  const current = historyResponse.verifications.find((item) => item.is_current);

  let currentVerificationId: string | null = null;
  let currentStatus: VerificationStatus | null = null;
  let reviewedBy: string | null = null;
  let blockchainStatus: BlockchainStatus | null = null;

  if (current) {
    currentVerificationId = current.verification_id;
    currentStatus = current.status;
    const verification = await getVerification(current.verification_id);
    const reviewActions = verification.review_actions ?? [];
    reviewedBy = reviewActions[0]?.reviewer_ref ?? null;
    const chain = await getBlockchain(current.verification_id);
    blockchainStatus = chain.recording_status;
  }

  return {
    documentId,
    fileName: document.original_filename,
    categoryLabel: categoryLabels[document.category] ?? document.category,
    uploadedAt: document.uploaded_at,
    currentVerificationId,
    currentStatus,
    blockchainStatus,
    history: historyResponse.verifications.map((item) => ({
      verificationId: item.verification_id,
      status: item.status,
      isCurrent: item.is_current,
      createdAt: item.created_at,
      reviewedBy: item.is_current ? reviewedBy : null,
    })),
  };
}

export function useRecentDocuments(): RecentDocumentsState {
  const documentIds = useRecentDocumentIds();
  const [rows, setRows] = useState<RecentDocumentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadVersion, setLoadVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      if (documentIds.length === 0) {
        if (!cancelled) {
          setRows([]);
          setError(null);
          setLoading(false);
        }
        return;
      }

      try {
        const types = await getDocumentTypes();
        const categoryLabels: Record<string, string> = {};
        for (const type of types) {
          categoryLabels[type.category] = type.label;
        }
        const hydrated = await Promise.all(documentIds.map((id) => hydrateRow(id, categoryLabels)));
        if (!cancelled) {
          setRows(hydrated);
          setError(null);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setRows([]);
          setError('Could not load the documents in this browser session.');
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [documentIds, loadVersion]);

  const reload = useCallback(() => {
    setLoading(true);
    setLoadVersion((version) => version + 1);
  }, []);

  return { loading, error, rows, reload };
}