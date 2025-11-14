import { z } from "zod";

/**
 * Feature progress schema
 */
export const FeatureProgress = z.object({
  done: z.number(),
  percent: z.number(),
});

/**
 * Product images features schema
 */
export const ProductImagesFeatures = z.object({
  total: z.number(),
  segment: FeatureProgress,
  embedding: FeatureProgress,
  keypoints: FeatureProgress,
});

/**
 * Video frames features schema
 */
export const VideoFramesFeatures = z.object({
  total: z.number(),
  segment: FeatureProgress,
  embedding: FeatureProgress,
  keypoints: FeatureProgress,
});

/**
 * Features summary response schema
 */
export const FeaturesSummaryResponse = z.object({
  job_id: z.string(),
  product_images: ProductImagesFeatures,
  video_frames: VideoFramesFeatures,
  updated_at: z.string().nullable(),
});

/**
 * Feature paths schema
 */
export const FeaturePaths = z.object({
  segment: z.string().nullable(),
  embedding: z.string().nullable(),
  keypoints: z.string().nullable(),
});

/**
 * Product image feature item schema
 */
export const ProductImageFeatureItem = z.object({
  img_id: z.string(),
  product_id: z.string(),
  original_url: z.string().nullable(),
  has_segment: z.boolean(),
  has_embedding: z.boolean(),
  has_keypoints: z.boolean(),
  paths: FeaturePaths,
  updated_at: z.string().nullable(),
});

/**
 * Product image features response schema
 */
export const ProductImageFeaturesResponse = z.object({
  items: z.array(ProductImageFeatureItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

/**
 * Video frame feature item schema
 */
export const VideoFrameFeatureItem = z.object({
  frame_id: z.string(),
  video_id: z.string(),
  ts: z.number(),
  original_url: z.string().nullable(),
  has_segment: z.boolean(),
  has_embedding: z.boolean(),
  has_keypoints: z.boolean(),
  paths: FeaturePaths,
  updated_at: z.string().nullable(),
});

/**
 * Video frame features response schema
 */
export const VideoFrameFeaturesResponse = z.object({
  items: z.array(VideoFrameFeatureItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

// Export types
export type FeatureProgress = z.infer<typeof FeatureProgress>;
export type ProductImagesFeatures = z.infer<typeof ProductImagesFeatures>;
export type VideoFramesFeatures = z.infer<typeof VideoFramesFeatures>;
export type FeaturesSummaryResponse = z.infer<typeof FeaturesSummaryResponse>;
export type FeaturePaths = z.infer<typeof FeaturePaths>;
export type ProductImageFeatureItem = z.infer<typeof ProductImageFeatureItem>;
export type ProductImageFeaturesResponse = z.infer<typeof ProductImageFeaturesResponse>;
export type VideoFrameFeatureItem = z.infer<typeof VideoFrameFeatureItem>;
export type VideoFrameFeaturesResponse = z.infer<typeof VideoFrameFeaturesResponse>;
