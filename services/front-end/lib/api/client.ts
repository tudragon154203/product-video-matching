import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * Configuration for API services
 */
interface ApiConfig {
  baseURL: string;
  timeout: number;
}

/**
 * Default API configuration
 */
const defaultConfig: ApiConfig = {
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8888',
  timeout: 30000,
};

/**
 * Create an axios instance with default configuration
 */
export function createApiClient(config: Partial<ApiConfig> = {}): AxiosInstance {
  const finalConfig = { ...defaultConfig, ...config };
  
  const client = axios.create({
    baseURL: finalConfig.baseURL,
    timeout: finalConfig.timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for common request modifications
  client.interceptors.request.use(
    (config) => {
      // Add any common request modifications here
      // e.g., authentication tokens, request ID, etc.
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for common error handling
  client.interceptors.response.use(
    (response) => {
      return response;
    },
    (error) => {
      // Common error handling
      if (error.response?.status === 401) {
        // Handle unauthorized access
        console.warn('Unauthorized access');
      }
      
      if (error.response?.status >= 500) {
        // Handle server errors
        console.error('Server error:', error.response.data);
      }
      
      return Promise.reject(error);
    }
  );

  return client;
}

/**
 * Main API client instance for main-api service
 */
export const mainApiClient = createApiClient();

/**
 * Results API client instance for results-api service
 */
export const resultsApiClient = createApiClient({
  baseURL: process.env.NEXT_PUBLIC_RESULTS_API_BASE_URL || 'http://localhost:8888',
});

/**
 * Generic API request function with type safety
 */
export async function apiRequest<T>(
  client: AxiosInstance,
  config: AxiosRequestConfig
): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}