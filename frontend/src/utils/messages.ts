import { ApiError } from '../api/client';
import type { BlockchainErrorCode } from '../types/api';
import { humanizeField } from './fields';

const WARNING_TRANSLATIONS: Record<string, (field: string) => string> = {
  'missing_field': (field) => humanizeField(field) + ' could not be read from the document',
  'low_confidence': (field) => humanizeField(field) + ' was read with low confidence',
  'no_text_detected': () => 'No text could be detected in the document',
  'unrecognized_date_format': (field) => humanizeField(field) + ' is not in the expected date format (YYYY-MM-DD)',
};

const BLOCKCHAIN_ERROR_TRANSLATIONS: Record<BlockchainErrorCode, string> = {
  RPC_UNAVAILABLE: 'Could not reach the blockchain network',
  TX_REVERTED: 'The blockchain network declined the submission',
  RECEIPT_TIMEOUT: 'The blockchain network did not confirm the submission in time',
  EVENT_MISMATCH: 'The on-chain event did not match the expected outcome record',
};

const DEFAULT_NETWORK_MESSAGE =
  'Could not reach the server. Check your connection and try again.';

/**
 * Returns a safe, human-readable message from any thrown value. Never passes a raw
 * exception message, stack trace, or "[object Object]" to the screen.
 */
export function safeMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof TypeError) {
    return DEFAULT_NETWORK_MESSAGE;
  }
  if (error instanceof Error && error.message && error.message !== '[object Object]') {
    return error.message;
  }
  return DEFAULT_NETWORK_MESSAGE;
}

/**
 * Converts any thrown value into the type used by state hooks. Network failures get a
 * friendly message; ApiError values pass through unchanged.
 */
export function toApiError(error: unknown, fallback: string): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof TypeError) {
    return new ApiError('NETWORK_ERROR', DEFAULT_NETWORK_MESSAGE, {}, 0);
  }
  if (error instanceof Error && error.message) {
    return new ApiError('UNKNOWN', error.message, {}, 0);
  }
  return new ApiError('UNKNOWN', fallback, {}, 0);
}

export function translateWarning(warning: string): string {
  const [code, ...rest] = warning.split(':');
  const field = rest.join(':');
  const translator = WARNING_TRANSLATIONS[code];
  if (translator) {
    return field ? translator(field) : translator('');
  }
  return warning;
}

export function translateBlockchainError(errorCode: BlockchainErrorCode | null): string | null {
  if (!errorCode) return null;
  return BLOCKCHAIN_ERROR_TRANSLATIONS[errorCode] ?? errorCode;
}

export function getUploadErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'FILE_TOO_LARGE':
        return 'That file is too large. The maximum upload size is 10 MB.';
      case 'UNSUPPORTED_MEDIA_TYPE':
        return 'That file type is not supported. Use a JPEG, PNG, or PDF.';
      case 'EMPTY_OR_CORRUPT_FILE':
        return 'The file appears to be empty or unreadable. Try another file.';
      case 'INVALID_CATEGORY':
        return 'The selected category is not recognised. Choose one of the listed categories.';
      default:
        return error.message;
    }
  }
  return safeMessage(error);
}

export function getVerifyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return 'Could not complete verification — technical error';
  }
  return safeMessage(error);
}