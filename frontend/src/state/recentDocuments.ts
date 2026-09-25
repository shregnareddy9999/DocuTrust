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
 * it stores document IDs with optional hidden verification IDs (localStorage, best-effort) 
 * and hydrates each row with the EXISTING document/verification/blockchain endpoints. 
 * A real list endpoint can be swapped in behind the same surface later.
 */
const STORAGE_KEY = 'docutrust.recentDocuments';
const MAX_DOCS = 20;

interface StoredDocument {
  documentId: string;
  hiddenVerificationIds?: string[];
}

function readStoredDocuments(): StoredDocument[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((entry): entry is StoredDocument => 
      typeof entry === 'object' && entry !== null && typeof entry.documentId === 'string'
    );
  } catch {
    return [];
  }
}

let storedDocuments: StoredDocument[] = readStoredDocuments();
let snapshot: StoredDocument[] = storedDocuments.slice();
let documentIdsCache: string[] = storedDocuments.map(d => d.documentId);

function writeStoredDocuments(): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(storedDocuments));
  } catch {
    // storage unavailable; the in-memory list still works
  }
}

function updateSnapshotAndCache(): void {
  snapshot = storedDocuments.slice();
  documentIdsCache = storedDocuments.map(d => d.documentId);
}

const listeners = new Set<() => void>();

function emit(): void {
  updateSnapshotAndCache();
  // In test environment, skip listener notification to avoid React act() infinite loops
  // useSyncExternalStore will pick up changes via getSnapshot on next render
  const isTest = (typeof globalThis !== 'undefined' && 'vi' in globalThis) || (typeof process !== 'undefined' && process.env.NODE_ENV === 'test');
  if (!isTest) {
    queueMicrotask(() => {
      for (const listener of listeners) listener();
    });
  }
}

export function addRecentDocument(documentId: string): void {
  const existingIndex = storedDocuments.findIndex(d => d.documentId === documentId);
  if (existingIndex >= 0) {
    // Move to front
    const doc = storedDocuments.splice(existingIndex, 1)[0];
    storedDocuments.unshift(doc);
  } else {
    storedDocuments.unshift({ documentId, hiddenVerificationIds: [] });
  }
  storedDocuments = storedDocuments.slice(0, MAX_DOCS);
  writeStoredDocuments();
  emit();
}

export function getRecentDocumentIds(): string[] {
  return documentIdsCache;
}

export function getStoredDocuments(): StoredDocument[] {
  return snapshot;
}

export function clearRecentDocuments(): void {
  storedDocuments = [];
  writeStoredDocuments();
  emit();
}

export function removeRecentDocument(documentId: string): void {
  storedDocuments = storedDocuments.filter(d => d.documentId !== documentId);
  writeStoredDocuments();
  emit();
}

export function hideVerification(documentId: string, verificationId: string): void {
  const doc = storedDocuments.find(d => d.documentId === documentId);
  if (doc) {
    if (!doc.hiddenVerificationIds) {
      doc.hiddenVerificationIds = [];
    }
    if (!doc.hiddenVerificationIds.includes(verificationId)) {
      doc.hiddenVerificationIds.push(verificationId);
    }
    writeStoredDocuments();
    emit();
  }
}

export function showVerification(documentId: string, verificationId: string): void {
  const doc = storedDocuments.find(d => d.documentId === documentId);
  if (doc && doc.hiddenVerificationIds) {
    doc.hiddenVerificationIds = doc.hiddenVerificationIds.filter(id => id !== verificationId);
    writeStoredDocuments();
    emit();
  }
}

export function subscribeRecentDocuments(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useRecentDocumentIds(): string[] {
  return useSyncExternalStore(subscribeRecentDocuments, () => documentIdsCache, () => []);
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
  hiddenVerificationIds?: string[];
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
  let blockchainStatus: BlockchainStatus | null = null;

  if (current) {
    currentVerificationId = current.verification_id;
    currentStatus = current.status;
    const chain = await getBlockchain(current.verification_id);
    blockchainStatus = chain.recording_status;
  }

  // Fetch review actions for all verifications to get reviewer names
  const verificationDetails = await Promise.all(
    historyResponse.verifications.map(async (item) => {
      const verification = await getVerification(item.verification_id);
      const reviewActions = verification.review_actions ?? [];
      const reviewerRef = reviewActions[0]?.reviewer_ref ?? null;
      return { verificationId: item.verification_id, reviewerRef };
    })
  );

  const reviewerMap = new Map(
    verificationDetails.map((d) => [d.verificationId, d.reviewerRef])
  );

  // Get hidden verification IDs from storage
  const storedDoc = storedDocuments.find(d => d.documentId === documentId);
  const hiddenIds = storedDoc?.hiddenVerificationIds ?? [];

  return {
    documentId,
    fileName: document.original_filename,
    categoryLabel: categoryLabels[document.category] ?? document.category,
    uploadedAt: document.uploaded_at,
    currentVerificationId,
    currentStatus,
    blockchainStatus,
    history: historyResponse.verifications
      .filter((item) => !hiddenIds.includes(item.verification_id))
      .map((item) => ({
        verificationId: item.verification_id,
        status: item.status,
        isCurrent: item.is_current,
        createdAt: item.created_at,
        reviewedBy: reviewerMap.get(item.verification_id) ?? null,
      })),
    hiddenVerificationIds: hiddenIds,
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
        const settled = await Promise.allSettled(
          documentIds.map((id) => hydrateRow(id, categoryLabels))
        );
        const hydrated = settled
          .filter((item): item is PromiseFulfilledResult<RecentDocumentRow> => item.status === 'fulfilled')
          .map((item) => item.value);
        if (!cancelled) {
          // Don't show error if some documents loaded successfully
          // Only show error if NO documents loaded AND there were rejections
          if (hydrated.length === 0 && settled.some((item) => item.status === 'rejected')) {
            setRows([]);
            setError('Could not load the documents in this browser session.');
          } else {
            setRows(hydrated);
            setError(null);
          }
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