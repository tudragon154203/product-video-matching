import { z } from "zod";

export const Phase = z.enum([
  "unknown",
  "collection", 
  "feature_extraction",
  "matching",
  "evidence",
  "completed",
  "failed",
  "cancelled",
]);

export const JobStatus = z.object({
  job_id: z.string(),
  phase: Phase,
  percent: z.number(),
  counts: z.object({
    products: z.number(),
    videos: z.number(),
    images: z.number(),
    frames: z.number(),
  }),
  collection: z
    .object({
      products_done: z.boolean(),
      videos_done: z.boolean(),
    })
    .optional(),
  updated_at: z.string().nullable(),
});

export const StartJobResponse = z.object({
  job_id: z.string(),
  status: z.literal("started"),
});

export const StartJobRequest = z.object({
  query: z.string().trim().min(1, { message: "Query must not be empty" }),
  top_amz: z.number().int().min(0).max(100),
  top_ebay: z.number().int().min(0).max(100),
  platforms: z.array(z.enum(["youtube", "douyin", "tiktok", "bilibili"])),
  recency_days: z.number().int().min(1).max(365),
});

export const JobItem = z.object({
  job_id: z.string(),
  query: z.string(),
  industry: z.string(),
  phase: z.string(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
  cancelled_at: z.string().nullable().optional(),
  deleted_at: z.string().nullable().optional(),
});

export const JobListResponse = z.object({
  items: z.array(JobItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const JobAssetTypes = z.object({
  images: z.boolean(),
  videos: z.boolean(),
}).transform((data) => ({
  ...data,
  job_type: data.images && data.videos ? "mixed" : 
           data.images ? "product-only" : 
           data.videos ? "video-only" : 
           "zero-asset"
}));

export const CancelJobRequest = z.object({
  reason: z.string().optional().default("user_request"),
  notes: z.string().optional(),
});

export const CancelJobResponse = z.object({
  job_id: z.string(),
  phase: z.string(),
  cancelled_at: z.string(),
  reason: z.string(),
  notes: z.string().nullable().optional(),
});

export const DeleteJobResponse = z.object({
  job_id: z.string(),
  status: z.string(),
  deleted_at: z.string(),
});

export type Phase = z.infer<typeof Phase>;
export type JobStatus = z.infer<typeof JobStatus>;
export type StartJobResponse = z.infer<typeof StartJobResponse>;
export type StartJobRequest = z.infer<typeof StartJobRequest>;
export type JobItem = z.infer<typeof JobItem>;
export type JobListResponse = z.infer<typeof JobListResponse>;
export type JobAssetTypes = z.infer<typeof JobAssetTypes>;
export type CancelJobRequest = z.infer<typeof CancelJobRequest>;
export type CancelJobResponse = z.infer<typeof CancelJobResponse>;
export type DeleteJobResponse = z.infer<typeof DeleteJobResponse>;
