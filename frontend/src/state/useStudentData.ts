import { useCallback, useEffect, useState } from 'react';
import { getGovernmentRecords, getMarksheetHistory, getStudentDocuments } from '../api/students';
import type {
  GovernmentRecordsResponse,
  MarksheetHistoryResponse,
  StudentDocumentLink,
} from '../types/api';

export interface StudentData {
  documents: StudentDocumentLink[];
  government: GovernmentRecordsResponse;
  marksheets: MarksheetHistoryResponse;
}

interface Loaded {
  ref: string;
  data: StudentData;
}

/**
 * Loads a student's records. It refetches when the student changes, when the tab regains focus or
 * becomes visible, and when `reload()` is called. It deliberately schedules nothing on a clock
 * (the project forbids scripted timers in app source); continuous push updates need a backend
 * transport that has not been approved yet.
 */
export function useStudentData(studentRef: string | null) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((value) => value + 1), []);

  useEffect(() => {
    if (!studentRef) return;
    let cancelled = false;

    async function load(ref: string, showSpinner: boolean) {
      if (showSpinner) setLoading(true);
      try {
        const [documents, government, marksheets] = await Promise.all([
          getStudentDocuments(ref),
          getGovernmentRecords(ref),
          getMarksheetHistory(ref),
        ]);
        if (!cancelled) {
          setLoaded({ ref, data: { documents, government, marksheets } });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load student records.');
      } finally {
        if (!cancelled && showSpinner) setLoading(false);
      }
    }

    const refresh = () => {
      if (document.visibilityState === 'visible') void load(studentRef, false);
    };

    void load(studentRef, true);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [studentRef, tick]);

  const data = loaded && loaded.ref === studentRef ? loaded.data : null;
  return { data, error, loading, reload };
}
