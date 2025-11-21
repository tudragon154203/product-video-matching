import { z } from "zod";

/**
 * Matching summary response schema
 */
export const MatchingSummaryResponse = z.object({
  job_id: z.string(),
  status: z.enum(['pending', 'running', 'completed', 'failed']),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  last_event_at: z.string().nullable(),
  candidates_total: z.number(),
  candidates_processed: z.number(),
  vector_pass_total: z.number(),
  vector_pass_done: z.number(),
  ransac_checked: z.number(),
  matches_found: z.number(),
  matches_with_evidence: z.number(),
  avg_score: z.number().nullable(),
  p90_score: z.number().nullable(),
  queue_depth: z.number(),
  eta_seconds: z.number().nullable(),
  blockers: z.array(z.string()),
});

export type MatchingSummaryResponse = z.infer<typeof MatchingSummaryResponse>;
