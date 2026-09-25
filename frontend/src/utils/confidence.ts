export const LOW_CONFIDENCE_THRESHOLD = 0.7;

export type OcrConfidenceSummary =
  | { state: 'none' }
  | { state: 'low'; percentage: number }
  | { state: 'read'; percentage: number };

export function describeOcrConfidence(confidence: number | null): OcrConfidenceSummary {
  if (confidence === null) return { state: 'none' };
  if (confidence < LOW_CONFIDENCE_THRESHOLD) return { state: 'low', percentage: confidence };
  return { state: 'read', percentage: confidence };
}

export function ocrConfidenceMessage(confidence: number | null): string {
  const summary = describeOcrConfidence(confidence);
  if (summary.state === 'low') {
    return 'Low confidence — OCR was unsure, may need human review';
  }
  if (summary.state === 'read') {
    return 'Read clearly';
  }
  return '—';
}

export function formatOcrConfidence(confidence: number | null): string {
  return confidence === null ? '—' : `${Math.round(confidence * 100)}%`;
}