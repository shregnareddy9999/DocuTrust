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

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ACCEPTED_UPLOAD_TYPES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']);

export const UPLOAD_ERROR_COPY = {
  FILE_TOO_LARGE: 'That file is too large. The maximum upload size is 10 MB.',
  UNSUPPORTED_MEDIA_TYPE: 'That file type is not supported. Use a JPEG, PNG, or PDF.',
  EMPTY_OR_CORRUPT_FILE: 'The file appears to be empty or unreadable. Try another file.',
  INVALID_CATEGORY: 'The selected category is not recognised. Choose one of the listed categories.',
} as const;

export function getClientUploadHint(file: File): string | null {
  if (file.size === 0) {
    return UPLOAD_ERROR_COPY.EMPTY_OR_CORRUPT_FILE;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return UPLOAD_ERROR_COPY.FILE_TOO_LARGE;
  }
  const name = file.name.toLowerCase();
  const hasAcceptedExtension =
    name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png') || name.endsWith('.pdf');
  const type = (file.type || '').toLowerCase();
  const hasAcceptedType = ACCEPTED_UPLOAD_TYPES.has(type);
  if (!hasAcceptedType && !hasAcceptedExtension) {
    return UPLOAD_ERROR_COPY.UNSUPPORTED_MEDIA_TYPE;
  }
  return null;
}

/**
 * Returns a safe, human-readable message from any thrown value. Never passes a raw
 * exception message, stack trace, or "[object Object]" to the screen.
 */
export function safeMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const mapped = getUploadErrorMessage(error);
    if (mapped !== DEFAULT_NETWORK_MESSAGE) {
      return mapped;
    }
    if (error.message && error.message !== '[object Object]') {
      return error.message;
    }
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
    return new ApiError('UNKNOWN', fallback, {}, 0);
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
        return UPLOAD_ERROR_COPY.FILE_TOO_LARGE;
      case 'UNSUPPORTED_MEDIA_TYPE':
        return UPLOAD_ERROR_COPY.UNSUPPORTED_MEDIA_TYPE;
      case 'EMPTY_OR_CORRUPT_FILE':
        return UPLOAD_ERROR_COPY.EMPTY_OR_CORRUPT_FILE;
      case 'INVALID_CATEGORY':
        return UPLOAD_ERROR_COPY.INVALID_CATEGORY;
      default:
        break;
    }
    switch (error.status) {
      case 413:
        return UPLOAD_ERROR_COPY.FILE_TOO_LARGE;
      case 415:
        return UPLOAD_ERROR_COPY.UNSUPPORTED_MEDIA_TYPE;
      case 422:
        return UPLOAD_ERROR_COPY.EMPTY_OR_CORRUPT_FILE;
      case 400:
        return UPLOAD_ERROR_COPY.INVALID_CATEGORY;
      default:
        break;
    }
    if (error.code === 'NETWORK_ERROR') {
      return DEFAULT_NETWORK_MESSAGE;
    }
  }
  return DEFAULT_NETWORK_MESSAGE;
}

export function getVerifyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return 'Could not complete verification — technical error';
  }
  return safeMessage(error);
}