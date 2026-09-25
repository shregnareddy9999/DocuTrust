import { describe, expect, it } from 'vitest';
import { safeMessage, translateWarning, translateBlockchainError, getUploadErrorMessage } from './messages';
import { ApiError } from '../api/client';

describe('safeMessage', () => {
  it('returns the error envelope message for ApiError', () => {
    const err = new ApiError('FILE_TOO_LARGE', 'The file exceeds the maximum upload size.', {}, 413);
    expect(safeMessage(err)).toBe('The file exceeds the maximum upload size.');
  });

  it('returns the exception message for ordinary errors', () => {
    expect(safeMessage(new Error('something broke'))).toBe('something broke');
  });

  it('never leaks "[object Object]" or raw non-Error values', () => {
    expect(safeMessage('[object Object]')).toBe('Could not reach the server. Check your connection and try again.');
    expect(safeMessage({ nope: true })).toBe('Could not reach the server. Check your connection and try again.');
  });
});

describe('translateWarning', () => {
  it('translates missing_field with a human-readable field name', () => {
    expect(translateWarning('missing_field:student_id')).toBe('Student ID could not be read from the document');
  });

  it('translates low_confidence', () => {
    expect(translateWarning('low_confidence:semester_or_year')).toBe('Semester or Year was read with low confidence');
  });

  it('leaves unknown warnings as-is', () => {
    expect(translateWarning('something_unknown:foo')).toBe('something_unknown:foo');
  });
});

describe('translateBlockchainError', () => {
  it('translates RPC_UNAVAILABLE to plain language', () => {
    expect(translateBlockchainError('RPC_UNAVAILABLE')).toBe('Could not reach the blockchain network');
  });

  it('returns null when no error code is present', () => {
    expect(translateBlockchainError(null)).toBeNull();
  });
});

describe('getUploadErrorMessage', () => {
  it('returns a distinct, useful message per error code', () => {
    expect(getUploadErrorMessage(new ApiError('FILE_TOO_LARGE', 'x', {}, 413))).toBe(
      'That file is too large. The maximum upload size is 10 MB.'
    );
    expect(getUploadErrorMessage(new ApiError('UNSUPPORTED_MEDIA_TYPE', 'x', {}, 415))).toBe(
      'That file type is not supported. Use a JPEG, PNG, or PDF.'
    );
    expect(getUploadErrorMessage(new ApiError('EMPTY_OR_CORRUPT_FILE', 'x', {}, 422))).toBe(
      'The file appears to be empty or unreadable. Try another file.'
    );
    expect(getUploadErrorMessage(new ApiError('INVALID_CATEGORY', 'x', {}, 400))).toBe(
      'The selected category is not recognised. Choose one of the listed categories.'
    );
  });

  it('falls back to a safe message for non-ApiError failures', () => {
    expect(getUploadErrorMessage(new Error('boom'))).toBe('boom');
  });
});