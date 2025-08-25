import { AxiosError } from 'axios';

/**
 * Standard API error structure
 */
export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: unknown;
}

/**
 * Error codes for different scenarios
 */
export const ErrorCodes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
} as const;

/**
 * Convert axios error to standardized API error
 */
export function transformAxiosError(error: AxiosError): ApiError {
  if (error.code === 'ECONNABORTED') {
    return {
      message: 'Request timeout. Please try again.',
      code: ErrorCodes.TIMEOUT_ERROR,
      status: 408,
    };
  }
  
  if (error.code === 'ERR_NETWORK') {
    return {
      message: 'Network error. Please check your connection.',
      code: ErrorCodes.NETWORK_ERROR,
      status: 0,
    };
  }
  
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    
    switch (status) {
      case 400:
        return {
          message: (data as any)?.message || 'Invalid request. Please check your input.',
          code: ErrorCodes.VALIDATION_ERROR,
          status,
          details: data,
        };
        
      case 401:
        return {
          message: 'Unauthorized. Please log in.',
          code: ErrorCodes.UNAUTHORIZED,
          status,
        };
        
      case 403:
        return {
          message: 'Access forbidden. You do not have permission.',
          code: ErrorCodes.FORBIDDEN,
          status,
        };
        
      case 404:
        return {
          message: (data as any)?.message || 'Resource not found.',
          code: ErrorCodes.NOT_FOUND,
          status,
        };
        
      case 429:
        return {
          message: 'Too many requests. Please wait and try again.',
          code: ErrorCodes.SERVER_ERROR,
          status,
        };
        
      default:
        if (status >= 500) {
          return {
            message: (data as any)?.message || 'Server error. Please try again later.',
            code: ErrorCodes.SERVER_ERROR,
            status,
            details: data,
          };
        }
    }
  }
  
  return {
    message: error.message || 'An unknown error occurred.',
    code: ErrorCodes.UNKNOWN_ERROR,
    details: error,
  };
}

/**
 * Check if error is a specific type
 */
export function isErrorType(error: unknown, errorCode: string): boolean {
  return (error as ApiError)?.code === errorCode;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: ApiError): boolean {
  return [
    ErrorCodes.NETWORK_ERROR,
    ErrorCodes.TIMEOUT_ERROR,
    ErrorCodes.SERVER_ERROR,
  ].includes(error.code as any);
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyMessage(error: ApiError): string {
  switch (error.code) {
    case ErrorCodes.NETWORK_ERROR:
      return 'Unable to connect to the server. Please check your internet connection.';
      
    case ErrorCodes.TIMEOUT_ERROR:
      return 'The request is taking longer than expected. Please try again.';
      
    case ErrorCodes.NOT_FOUND:
      return 'The requested information could not be found.';
      
    case ErrorCodes.UNAUTHORIZED:
      return 'You need to log in to access this feature.';
      
    case ErrorCodes.FORBIDDEN:
      return 'You do not have permission to perform this action.';
      
    case ErrorCodes.VALIDATION_ERROR:
      return error.message || 'Please check your input and try again.';
      
    case ErrorCodes.SERVER_ERROR:
      return 'We are experiencing technical difficulties. Please try again later.';
      
    default:
      return error.message || 'Something went wrong. Please try again.';
  }
}

/**
 * Handle API errors consistently
 */
export function handleApiError(error: unknown): ApiError {
  if (error instanceof Error && 'isAxiosError' in error) {
    return transformAxiosError(error as AxiosError);
  }
  
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return error as ApiError;
  }
  
  return {
    message: 'An unexpected error occurred.',
    code: ErrorCodes.UNKNOWN_ERROR,
    details: error,
  };
}