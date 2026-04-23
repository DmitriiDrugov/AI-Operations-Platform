import { z } from 'zod';
import { InteractionType } from '../enums/index.js';
import { KnowledgeChunkSchema } from '../entities/index.js';

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

export const PaginationSchema = z.object({
  page: z.number().int().min(1).default(1),
  limit: z.number().int().min(1).max(100).default(20),
});
export type Pagination = z.infer<typeof PaginationSchema>;

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    total: z.number().int(),
    page: z.number().int(),
    limit: z.number().int(),
    has_more: z.boolean(),
  });

// ---------------------------------------------------------------------------
// API error envelope
// ---------------------------------------------------------------------------

export const ApiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.unknown()).optional(),
    trace_id: z.string().optional(),
  }),
});
export type ApiError = z.infer<typeof ApiErrorSchema>;

// ---------------------------------------------------------------------------
// Copilot API
// ---------------------------------------------------------------------------

export const CopilotQueryRequestSchema = z.object({
  query: z.string().min(1).max(2000),
  context: z.object({
    guest_id: z.string().uuid().optional(),
    stay_id: z.string().uuid().optional(),
    interaction_type: z.nativeEnum(InteractionType),
  }),
  organisation_id: z.string().uuid(),
  user_id: z.string().uuid(),
});
export type CopilotQueryRequest = z.infer<typeof CopilotQueryRequestSchema>;

export const CitationSchema = z.object({
  chunk_id: z.string().uuid(),
  page_title: z.string(),
  section_heading: z.string().nullable(),
  similarity_score: z.number().min(0).max(1),
  source_url: z.string().url().nullable(),
});
export type Citation = z.infer<typeof CitationSchema>;

export const SuggestedActionSchema = z.object({
  action_type: z.enum([
    'create_appointment',
    'send_message',
    'add_note',
    'update_lead_status',
    'generate_invoice',
    'escalate',
  ]),
  label: z.string(),
  payload: z.record(z.unknown()),
});
export type SuggestedAction = z.infer<typeof SuggestedActionSchema>;

export const CopilotQueryResponseSchema = z.object({
  response_text: z.string(),
  citations: z.array(CitationSchema),
  suggested_actions: z.array(SuggestedActionSchema),
  interaction_id: z.string().uuid(),
  model: z.string(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  latency_ms: z.number().int(),
});
export type CopilotQueryResponse = z.infer<typeof CopilotQueryResponseSchema>;

// ---------------------------------------------------------------------------
// Knowledge Search API
// ---------------------------------------------------------------------------

export const KnowledgeSearchRequestSchema = z.object({
  query: z.string().min(1).max(500),
  organisation_id: z.string().uuid(),
  source_types: z
    .array(z.enum(['notion_page', 'uploaded_doc', 'manual_entry']))
    .optional(),
  limit: z.number().int().min(1).max(20).default(8),
  min_similarity: z.number().min(0).max(1).default(0.72),
});
export type KnowledgeSearchRequest = z.infer<typeof KnowledgeSearchRequestSchema>;

export const KnowledgeSearchResponseSchema = z.object({
  results: z.array(
    KnowledgeChunkSchema.extend({ similarity_score: z.number() })
  ),
  query_embedding_latency_ms: z.number().int(),
  search_latency_ms: z.number().int(),
});
export type KnowledgeSearchResponse = z.infer<typeof KnowledgeSearchResponseSchema>;

// ---------------------------------------------------------------------------
// Lead Classification API
// ---------------------------------------------------------------------------

export const ClassifyLeadRequestSchema = z.object({
  inquiry_text: z.string().min(1).max(5000),
  organisation_id: z.string().uuid(),
  available_programmes: z.array(
    z.object({
      id: z.string().uuid(),
      name: z.string(),
      description: z.string().nullable(),
    })
  ),
});
export type ClassifyLeadRequest = z.infer<typeof ClassifyLeadRequestSchema>;

export const ClassifyLeadResponseSchema = z.object({
  intent: z.enum([
    'booking_inquiry',
    'general_question',
    'complaint',
    'referral',
    'other',
  ]),
  urgency: z.enum(['high', 'medium', 'low']),
  suggested_programme_ids: z.array(z.string().uuid()),
  budget_indicator: z.enum(['budget', 'mid', 'premium', 'unknown']),
  summary: z.string(),
  suggested_reply_draft: z.string(),
});
export type ClassifyLeadResponse = z.infer<typeof ClassifyLeadResponseSchema>;

// ---------------------------------------------------------------------------
// Billable Event Creation
// ---------------------------------------------------------------------------

export const CreateBillableEventRequestSchema = z.object({
  organisation_id: z.string().uuid(),
  guest_id: z.string().uuid(),
  stay_id: z.string().uuid().optional(),
  appointment_id: z.string().uuid().optional(),
  service_id: z.string().uuid().optional(),
  event_type: z.enum([
    'treatment',
    'product_sale',
    'room_charge',
    'extra_service',
    'penalty',
    'adjustment',
    'deposit',
  ]),
  description: z.string().min(1).max(500),
  quantity: z.number().positive(),
  unit_price: z.number().nonnegative(),
  currency: z.string().length(3),
  idempotency_key: z.string().min(1).max(255),
  occurred_at: z.string().datetime(),
});
export type CreateBillableEventRequest = z.infer<
  typeof CreateBillableEventRequestSchema
>;

// ---------------------------------------------------------------------------
// Outbox event shape (shared between Python and TypeScript)
// ---------------------------------------------------------------------------

export const OutboxEventSchema = z.object({
  id: z.string().uuid(),
  organisation_id: z.string().uuid(),
  event_type: z.string(),
  aggregate_type: z.string(),
  aggregate_id: z.string().uuid(),
  payload: z.record(z.unknown()),
  version: z.string().default('1'),
  metadata: z
    .object({
      source_service: z.string().optional(),
      trace_id: z.string().optional(),
    })
    .optional(),
  created_at: z.string().datetime(),
});
export type OutboxEvent = z.infer<typeof OutboxEventSchema>;
