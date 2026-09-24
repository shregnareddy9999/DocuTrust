const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export class ApiError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly status: number;

  constructor(code: string, message: string, details: Record<string, unknown>, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let errorData: { error?: { code: string; message: string; details?: Record<string, unknown> } };
  try {
    errorData = await response.json();
  } catch {
    return new ApiError(
      'INTERNAL_ERROR',
      `HTTP ${response.status}: ${response.statusText}`,
      {},
      response.status
    );
  }

  const error = errorData.error ?? {
    code: 'INTERNAL_ERROR',
    message: `HTTP ${response.status}: ${response.statusText}`,
    details: {},
  };

  return new ApiError(error.code, error.message, error.details ?? {}, response.status);
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const headers: HeadersInit = {
    ...(options.headers ?? {}),
  };

  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}