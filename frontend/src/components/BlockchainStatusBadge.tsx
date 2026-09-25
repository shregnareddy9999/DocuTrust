import type { BlockchainResponse } from '../types/api';
import { StatusBadge } from './StatusBadge';

interface BlockchainStatusBadgeProps {
  blockchain: BlockchainResponse | null;
}

/**
 * Blockchain recording badge. Kept as its own component (never merged into a
 * verification badge) but delegates the label/colour mapping to StatusBadge.
 */
export function BlockchainStatusBadge({ blockchain }: BlockchainStatusBadgeProps) {
  return <StatusBadge kind="blockchain" blockchain={blockchain} />;
}