import { describe, expect, it } from 'vitest';
import {
  LOW_CONFIDENCE_THRESHOLD,
  describeOcrConfidence,
  formatOcrConfidence,
  ocrConfidenceMessage,
} from './confidence';

describe('describeOcrConfidence', () => {
  it('uses a single documented 0.70 threshold', () => {
    expect(LOW_CONFIDENCE_THRESHOLD).toBe(0.7);
  });

  it('labels values below 0.70 as low', () => {
    expect(describeOcrConfidence(0.69).state).toBe('low');
    expect(ocrConfidenceMessage(0.69)).toBe('Low confidence — OCR was unsure, may need human review');
  });

  it('labels 0.70 and above as read clearly', () => {
    expect(describeOcrConfidence(0.7).state).toBe('read');
    expect(ocrConfidenceMessage(0.7)).toBe('Read clearly');
    expect(ocrConfidenceMessage(0.94)).toBe('Read clearly');
  });

  it('handles a missing value as none', () => {
    expect(describeOcrConfidence(null).state).toBe('none');
    expect(ocrConfidenceMessage(null)).toBe('—');
  });

  it('formats OCR confidence as a whole percentage', () => {
    expect(formatOcrConfidence(0.94)).toBe('94%');
    expect(formatOcrConfidence(0.699)).toBe('70%');
    expect(formatOcrConfidence(null)).toBe('—');
  });
});