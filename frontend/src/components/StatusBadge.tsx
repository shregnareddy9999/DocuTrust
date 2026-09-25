import type { BlockchainResponse, VerificationStatus } from '../types/api';

export type BadgeKind = 'verification' | 'blockchain';

export type StatusBadgeProps =
  | { kind?: 'verification'; status: VerificationStatus }
  | { kind: 'blockchain'; blockchain: BlockchainResponse | null };

/** Sole verification status → label/colour mapping in the app. */
const VERIFICATION_META: Record<VerificationStatus, { label: string; className: string }> = {
  PENDING: { label: 'Processing…', className: 'status-badge status-badge--pending' },
  VERIFIED_MATCH: {
    label: 'Matched our synthetic demo reference',
    className: 'status-badge status-badge--matched',
  },
  REVIEW_REQUIRED: { label: 'Needs human review', className: 'status-badge status-badge--review' },
  NO_TRUSTED_RECORD: {
    label: 'No matching reference found in the demo registry — not evidence of a fake document',
    className: 'status-badge status-badge--norecord',
  },
  INTEGRITY_MISMATCH: { label: 'Mismatch found', className: 'status-badge status-badge--mismatch' },
  PROCESSING_FAILED: {
    label: 'Could not complete verification — technical error',
    className: 'status-badge status-badge--failed',
  },
};

/** Blockchain recording status → label/colour mapping. Never merged into a verification badge. */
const BLOCKCHAIN_META: Record<
  BlockchainResponse['recording_status'],
  { label: string; className: string }
> = {
  NOT_REQUESTED: {
    label: 'Not recorded on-chain',
    className: 'chain-badge chain-badge--not-requested',
  },
  PENDING: { label: 'On-chain recording pending', className: 'chain-badge chain-badge--pending' },
  CONFIRMED: {
    label: 'Verification outcome recorded on-chain',
    className: 'chain-badge chain-badge--confirmed',
  },
  FAILED: { label: 'On-chain recording failed', className: 'chain-badge chain-badge--failed' },
};

export function StatusBadge(props: StatusBadgeProps) {
  if (props.kind === 'blockchain') {
    const status = props.blockchain?.recording_status ?? 'NOT_REQUESTED';
    const meta = BLOCKCHAIN_META[status];
    return <span className={meta.className}>{meta.label}</span>;
  }
  const meta = VERIFICATION_META[props.status] ?? VERIFICATION_META.PENDING;
  return <span className={meta.className}>{meta.label}</span>;
}