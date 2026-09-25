import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { StatusBadge } from './components/StatusBadge';
import type { VerificationStatus } from './types/api';

const STATUSES: VerificationStatus[] = [
  'PENDING',
  'VERIFIED_MATCH',
  'REVIEW_REQUIRED',
  'NO_TRUSTED_RECORD',
  'INTEGRITY_MISMATCH',
  'PROCESSING_FAILED',
];

const DOCUMENTED_LABELS: Record<VerificationStatus, string> = {
  PENDING: 'Processing…',
  VERIFIED_MATCH: 'Matched our synthetic demo reference',
  REVIEW_REQUIRED: 'Needs human review',
  NO_TRUSTED_RECORD: 'No matching reference found in the demo registry — not evidence of a fake document',
  INTEGRITY_MISMATCH: 'Mismatch found',
  PROCESSING_FAILED: 'Could not complete verification — technical error',
};

const BANNED_WORDS = ['Verified', 'Authentic', 'Genuine', 'Valid', 'Invalid', 'Forged', 'Rejected', 'Fraud'];

function wholeWord(word: string): RegExp {
  return new RegExp(`\\b${word}\\b`, 'i');
}

describe('StatusBadge wording contract', () => {
  it('never uses a banned word for any status', () => {
    render(
      <>
        {STATUSES.map((status) => (
          <StatusBadge key={status} status={status} />
        ))}
      </>
    );
    const container = document.body.textContent ?? '';
    for (const word of BANNED_WORDS) {
      expect(container).not.toMatch(wholeWord(word));
    }
  });

  it('never mentions tampering in any status', () => {
    render(
      <>
        {STATUSES.map((status) => (
          <StatusBadge key={status} status={status} />
        ))}
      </>
    );
    const container = document.body.textContent ?? '';
    expect(container).not.toMatch(/tamper/i);
  });

  it('restricts "fake" to the NO_TRUSTED_RECORD explanation', () => {
    for (const status of STATUSES) {
      const { unmount } = render(<StatusBadge status={status} />);
      const badge = document.body.querySelector(`.status-badge`);
      expect(badge).not.toBeNull();
      const label = badge?.textContent ?? '';
      if (status === 'NO_TRUSTED_RECORD') {
        expect(label).toMatch(/not evidence of a fake document/);
      } else {
        expect(label).not.toMatch(wholeWord('fake'));
      }
      unmount();
    }
  });

  it('renders the exact documented label for each status', () => {
    for (const status of STATUSES) {
      const { unmount } = render(<StatusBadge status={status} />);
      const badge = document.body.querySelector(`.status-badge`);
      expect(badge).not.toBeNull();
      expect(badge?.textContent).toBe(DOCUMENTED_LABELS[status]);
      unmount();
    }
  });

  it('renders NO_TRUSTED_RECORD as clearly not evidence of a fake document', () => {
    const { getByText } = render(<StatusBadge status="NO_TRUSTED_RECORD" />);
    expect(getByText(/not evidence of a fake document/)).toBeInTheDocument();
  });
});

const RAW_SOURCES = import.meta.glob('./**/*.{ts,tsx,css}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>;

describe('source-wide banned word scan', () => {
  const sources = Object.entries(RAW_SOURCES).filter(
    ([path]) => !path.includes('.test.') && !path.includes('/test/') && !path.includes('setup')
  );

  it('finds source files to scan', () => {
    expect(sources.length).toBeGreaterThan(0);
  });

  it('contains no banned word anywhere in non-test source', () => {
    const words = [
      'Verified',
      'Authentic',
      'Genuine',
      'Invalid',
      'Forged',
      'Rejected',
      'Fraud',
      'Tamper-proof',
      'Tamper proof',
    ];
    const source = sources.map(([, content]) => content).join('\n');
    for (const word of words) {
      expect(source, `banned word: ${word}`).not.toMatch(wholeWord(word));
    }
  });

  it('contains no "Valid" outside the schema field label "valid_until"', () => {
    for (const [path, content] of sources) {
      const lines = content.split('\n');
      for (const line of lines) {
        if (wholeWord('Valid').test(line)) {
          const isSchemaLabel =
            line.includes("name: 'valid_until'") && line.includes("label: 'Valid Until'");
          expect(isSchemaLabel, `Unexpected "Valid" in ${path}: ${line.trim()}`).toBe(true);
        }
      }
    }
  });

  it('contains "fake" only inside the NO_TRUSTED_RECORD explanation', () => {
    for (const [path, content] of sources) {
      const lines = content.split('\n');
      for (const line of lines) {
        if (wholeWord('Fake').test(line)) {
          const isNoTrustedRecordLabel = line.includes(
            'No matching reference found in the demo registry'
          );
          expect(
            isNoTrustedRecordLabel,
            `Unexpected "fake" in ${path}: ${line.trim()}`
          ).toBe(true);
        }
      }
    }
  });
});