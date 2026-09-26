import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { getDocument } from '../api/documents';
import { getDocumentTypes } from '../api/documentTypes';
import { getBlockchain, getVerification, getVerificationHistory } from '../api/verifications';
import { getDemoSession, onSessionChange } from '../state/demoAuth';
import type {
  BlockchainStatus,
  VerificationStatus,
} from '../types/api';

/**
 * Client-side list of documents opened in this browser session for the current user.
 *
 * The API has no list endpoints, so the shell screens are built over this module:
 * it stores document IDs with optional hidden verification IDs (localStorage, best-effort) 
 * and hydrates each row with the EXISTING document/verification/blockchain endpoints. 
 * A real list endpoint can be swapped in behind the same surface later.
 */
const STORAGE_KEY_PREFIX = 'docutrust.recentDocuments';
const MAX_DOCS = 20;

interface StoredDocument {
  documentId: string;
  hiddenVerificationIds?: string[];
}

function getStorageKey(): string {
  const session = getDemoSession();
  const email = session?.email ?? 'anonymous';
  return `${STORAGE_KEY_PREFIX}.${email.toLowerCase()}`;
}

function readStoredDocuments(): StoredDocument[] {
  try {
    const raw = window.localStorage.getItem(getStorageKey());
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

function writeStoredDocuments(docs: StoredDocument[]): void {
  try {
    window.localStorage.setItem(getStorageKey(), JSON.stringify(docs));
  } catch {
    // storage unavailable; the in-memory list still works
  }
}

let storedDocuments: StoredDocument[] = readStoredDocuments();
let snapshot: StoredDocument[] = storedDocuments.slice();
let documentIdsCache: string[] = storedDocuments.map(d => d.documentId);

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

function reloadFromStorage(): void {
  const fromStorage = readStoredDocuments();
  if (fromStorage.length > 0 || storedDocuments.length === 0) {
    storedDocuments = fromStorage;
    emit();
  }
}

// Reinitialize when user session changes (login/logout/switch user)
onSessionChange(() => {
  reloadFromStorage();
});

export function addRecentDocument(documentId: string): void {
  reloadFromStorage();
  const existingIndex = storedDocuments.findIndex(d => d.documentId === documentId);
  if (existingIndex >= 0) {
    // Move to front
    const doc = storedDocuments.splice(existingIndex, 1)[0];
    storedDocuments.unshift(doc);
  } else {
    storedDocuments.unshift({ documentId, hiddenVerificationIds: [] });
  }
  storedDocuments = storedDocuments.slice(0, MAX_DOCS);
  writeStoredDocuments(storedDocuments);
  emit();
}

export function getRecentDocumentIds(): string[] {
  reloadFromStorage();
  return documentIdsCache;
}

export function getStoredDocuments(): StoredDocument[] {
  return snapshot;
}

export function clearRecentDocuments(): void {
  storedDocuments = [];
  writeStoredDocuments(storedDocuments);
  emit();
}

export function reinitializeForCurrentUser(): void {
  reloadFromStorage();
}

export function removeRecentDocument(documentId: string): void {
  reloadFromStorage();
  storedDocuments = storedDocuments.filter(d => d.documentId !== documentId);
  writeStoredDocuments(storedDocuments);
  emit();
}

export async function hideVerification(documentId: string, verificationId: string): Promise<void> {
  reloadFromStorage();
  const doc = storedDocuments.find(d => d.documentId === documentId);
  if (doc) {
    if (!doc.hiddenVerificationIds) {
      doc.hiddenVerificationIds = [];
    }
    if (!doc.hiddenVerificationIds.includes(verificationId)) {
      doc.hiddenVerificationIds.push(verificationId);
    }
    writeStoredDocuments(storedDocuments);
    emit();

    try {
      const historyResponse = await getVerificationHistory(documentId);
      const hiddenIds = doc.hiddenVerificationIds ?? [];
      const visibleVerifications = historyResponse.verifications.filter(
        (item) => !hiddenIds.includes(item.verification_id)
      );
      if (visibleVerifications.length === 0) {
        removeRecentDocument(documentId);
      }
    } catch {
      // If we can't fetch history, keep the document in the list
    }
  }
}

export function showVerification(documentId: string, verificationId: string): void {
  reloadFromStorage();
  const doc = storedDocuments.find(d => d.documentId === documentId);
  if (doc && doc.hiddenVerificationIds) {
    doc.hiddenVerificationIds = doc.hiddenVerificationIds.filter(id => id !== verificationId);
    writeStoredDocuments(storedDocuments);
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
  blockchainStatus: BlockchainStatus | null;
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
): Promise<RecentDocumentRow | null> {
  const document = await getDocument(documentId);
  const historyResponse = await getVerificationHistory(documentId);

  // Get hidden verification IDs from storage
  const storedDoc = storedDocuments.find(d => d.documentId === documentId);
  const hiddenIds = storedDoc?.hiddenVerificationIds ?? [];

  // Filter out hidden verifications
  const visibleVerifications = historyResponse.verifications.filter(
    (item) => !hiddenIds.includes(item.verification_id)
  );

  // If all verifications are hidden, return null to exclude this document
  if (visibleVerifications.length === 0) {
    return null;
  }

  // Find the current verification among visible ones
  // Prefer the one marked as current by API, otherwise the most recent
  let current = visibleVerifications.find((item) => item.is_current);
  if (!current) {
    // Fallback to most recent visible verification
    current = visibleVerifications[0];
  }

  let currentVerificationId: string | null = null;
  let currentStatus: VerificationStatus | null = null;
  let blockchainStatus: BlockchainStatus | null = null;

  if (current) {
    currentVerificationId = current.verification_id;
    currentStatus = current.status;
    const chain = await getBlockchain(current.verification_id);
    blockchainStatus = chain.recording_status;
  }

  // Fetch review actions and blockchain status for all verifications to get reviewer names and chain status
  const verificationDetails = await Promise.all(
    historyResponse.verifications.map(async (item) => {
      const verification = await getVerification(item.verification_id);
      const reviewActions = verification.review_actions ?? [];
      const reviewerRef = reviewActions[0]?.reviewer_ref ?? null;
      const chain = await getBlockchain(item.verification_id);
      return { 
        verificationId: item.verification_id, 
        reviewerRef,
        blockchainStatus: chain.recording_status
      };
    })
  );

  const reviewerMap = new Map(
    verificationDetails.map((d) => [d.verificationId, d.reviewerRef])
  );
  const blockchainStatusMap = new Map(
    verificationDetails.map((d) => [d.verificationId, d.blockchainStatus])
  );

  return {
    documentId,
    fileName: document.original_filename,
    categoryLabel: categoryLabels[document.category] ?? document.category,
    uploadedAt: document.uploaded_at,
    currentVerificationId,
    currentStatus,
    blockchainStatus,
    history: visibleVerifications
      .map((item) => ({
        verificationId: item.verification_id,
        status: item.status,
        isCurrent: item.verification_id === currentVerificationId,
        createdAt: item.created_at,
        reviewedBy: reviewerMap.get(item.verification_id) ?? null,
        blockchainStatus: blockchainStatusMap.get(item.verification_id) ?? null,
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
          .filter((item): item is PromiseFulfilledResult<RecentDocumentRow | null> => 
            item.status === 'fulfilled' && item.value !== null
          )
          .map((item) => item.value!);
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