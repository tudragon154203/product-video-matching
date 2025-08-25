import { z } from 'zod';

/**
 * Generic API response wrapper
 */
export const ApiResponse = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    success: z.boolean(),
    message: z.string().optional(),
    timestamp: z.string().optional(),
  });

/**
 * Generic API error response
 */
export const ApiErrorResponse = z.object({
  error: z.string(),
  message: z.string(),
  status: z.number(),
  timestamp: z.string().optional(),
});

/**
 * Generic paginated response wrapper
 */
export const PaginatedResponse = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    total: z.number(),
    limit: z.number(),
    offset: z.number(),
    has_next: z.boolean().optional(),
    has_prev: z.boolean().optional(),
  });

/**
 * Validation helper for API responses
 */
export function validateApiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown
): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(`API response validation failed: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Safe validation that returns null on error
 */
export function safeValidateApiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown
): T | null {
  try {
    return schema.parse(data);
  } catch {
    return null;
  }
}

// Export types
export type ApiResponse<T> = z.infer<ReturnType<typeof ApiResponse<z.ZodType<T>>>>;
export type ApiErrorResponse = z.infer<typeof ApiErrorResponse>;
export type PaginatedResponse<T> = z.infer<ReturnType<typeof PaginatedResponse<z.ZodType<T>>>>;