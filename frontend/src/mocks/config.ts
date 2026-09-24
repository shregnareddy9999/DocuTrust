import type { VerificationStatus } from '../types/api';

export interface MockConfig {
  mock: VerificationStatus | null;
  chain: string | null;
  err: string | null;
  net: boolean;
  slow: boolean;
}

const EMPTY: MockConfig = { mock: null, chain: null, err: null, net: false, slow: false };

let config: MockConfig = { ...EMPTY };

export function getMockConfig(): MockConfig {
  return config;
}

export function setMockConfig(next: Partial<MockConfig>): void {
  config = { ...config, ...next };
}

export function resetMockConfig(): void {
  config = { ...EMPTY };
}

export function initMockConfigFromUrl(search: string): void {
  const params = new URLSearchParams(search);
  config = {
    mock: (params.get('mock') as VerificationStatus | null) ?? null,
    chain: params.get('chain'),
    err: params.get('err'),
    net: params.get('net') === '1',
    slow: params.get('slow') === '1',
  };
}