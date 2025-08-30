import { z } from "zod";

/**
 * Image item schema for main-api image endpoints
 */
export const ImageItem = z.object({
  img_id: z.string(),
  product_id: z.string(),
  local_path: z.string(),
  url: z.string().nullable().optional(),
  product_title: z.string(),
  updated_at: z.string(),
});

/**
 * Image list response schema with pagination
 */
export const ImageListResponse = z.object({
  items: z.array(ImageItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

// Export types
export type ImageItem = z.infer<typeof ImageItem>;
export type ImageListResponse = z.infer<typeof ImageListResponse>;