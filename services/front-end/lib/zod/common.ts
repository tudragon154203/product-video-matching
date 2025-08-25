import { z } from "zod";

/**
 * Common pagination parameters
 */
export const PaginationParams = z.object({
  limit: z.number().int().min(1).max(1000).optional(),
  offset: z.number().int().min(0).optional(),
});

/**
 * Common sorting parameters
 */
export const SortParams = z.object({
  sort_by: z.string().optional(),
  order: z.enum(["ASC", "DESC"]).optional(),
});

/**
 * Combined pagination and sorting parameters
 */
export const PaginationSortParams = PaginationParams.merge(SortParams);

/**
 * Search query parameter
 */
export const SearchParams = z.object({
  q: z.string().optional(),
});

/**
 * Feature filter parameters
 */
export const FeatureFilterParams = z.object({
  has: z.enum(["segment", "embedding", "keypoints", "none", "any"]).optional(),
});

/**
 * Product filter parameters
 */
export const ProductFilterParams = z.object({
  src: z.string().optional(),
}).merge(SearchParams);

/**
 * Video filter parameters
 */
export const VideoFilterParams = z.object({
  platform: z.string().optional(),
  min_frames: z.number().int().min(0).optional(),
}).merge(SearchParams);

/**
 * Image filter parameters
 */
export const ImageFilterParams = z.object({
  product_id: z.string().optional(),
}).merge(SearchParams);

// Export types
export type PaginationParams = z.infer<typeof PaginationParams>;
export type SortParams = z.infer<typeof SortParams>;
export type PaginationSortParams = z.infer<typeof PaginationSortParams>;
export type SearchParams = z.infer<typeof SearchParams>;
export type FeatureFilterParams = z.infer<typeof FeatureFilterParams>;
export type ProductFilterParams = z.infer<typeof ProductFilterParams>;
export type VideoFilterParams = z.infer<typeof VideoFilterParams>;
export type ImageFilterParams = z.infer<typeof ImageFilterParams>;