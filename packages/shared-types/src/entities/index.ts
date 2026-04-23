import { z } from 'zod';
import {
  UserRole,
  LeadSource,
  LeadStatus,
  StayStatus,
  AppointmentStatus,
  BillableEventType,
  ApprovalStatus,
  InvoiceStatus,
} from '../enums/index.js';

// ---------------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------------

export const BaseEntitySchema = z.object({
  id: z.string().uuid(),
  organisation_id: z.string().uuid(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

// ---------------------------------------------------------------------------
// Organisation
// ---------------------------------------------------------------------------

export const OrganisationSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(255),
  slug: z.string().min(1).max(100).regex(/^[a-z0-9-]+$/),
  plan: z.string(),
  settings: z.record(z.unknown()),
  timezone: z.string(),
  currency: z.string().length(3),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Organisation = z.infer<typeof OrganisationSchema>;

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

export const UserSchema = z.object({
  id: z.string().uuid(),
  organisation_id: z.string().uuid(),
  role: z.nativeEnum(UserRole),
  full_name: z.string().min(1).max(255),
  avatar_url: z.string().url().nullable(),
  is_active: z.boolean(),
  last_seen_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type User = z.infer<typeof UserSchema>;

// ---------------------------------------------------------------------------
// Guest
// ---------------------------------------------------------------------------

export const GuestSchema = BaseEntitySchema.extend({
  external_id: z.string().nullable(),
  first_name: z.string().min(1).max(100),
  last_name: z.string().min(1).max(100),
  // Decrypted at service layer; transmitted as plaintext over TLS
  email: z.string().email().nullable(),
  phone: z.string().nullable(),
  date_of_birth: z.string().date().nullable(),
  nationality: z.string().length(2).nullable(),
  preferred_language: z.string().length(5).default('en'),
  gender: z.string().nullable(),
  referral_source: z.string().nullable(),
  tags: z.array(z.string()),
  internal_notes: z.string().nullable(),
  gdpr_consented_at: z.string().datetime().nullable(),
  marketing_consent: z.boolean(),
  is_vip: z.boolean(),
  profile_completeness: z.number().int().min(0).max(100),
});
export type Guest = z.infer<typeof GuestSchema>;

export const CreateGuestSchema = GuestSchema.omit({
  id: true,
  organisation_id: true,
  created_at: true,
  updated_at: true,
  profile_completeness: true,
});
export type CreateGuest = z.infer<typeof CreateGuestSchema>;

// ---------------------------------------------------------------------------
// Lead
// ---------------------------------------------------------------------------

export const LeadSchema = BaseEntitySchema.extend({
  guest_id: z.string().uuid().nullable(),
  source: z.nativeEnum(LeadSource),
  status: z.nativeEnum(LeadStatus),
  inquiry_text: z.string().nullable(),
  preferred_programme: z.string().nullable(),
  budget_indicator: z.enum(['budget', 'mid', 'premium', 'unknown']).nullable(),
  inquiry_date: z.string().date(),
  assigned_to: z.string().uuid().nullable(),
  last_contacted_at: z.string().datetime().nullable(),
  follow_up_at: z.string().datetime().nullable(),
  converted_at: z.string().datetime().nullable(),
  closed_at: z.string().datetime().nullable(),
  close_reason: z.string().nullable(),
  ai_summary: z.string().nullable(),
  ai_suggested_action: z.string().nullable(),
  metadata: z.record(z.unknown()),
});
export type Lead = z.infer<typeof LeadSchema>;

// ---------------------------------------------------------------------------
// Stay
// ---------------------------------------------------------------------------

export const StaySchema = BaseEntitySchema.extend({
  guest_id: z.string().uuid(),
  room_id: z.string().uuid().nullable(),
  programme_id: z.string().uuid().nullable(),
  status: z.nativeEnum(StayStatus),
  check_in_date: z.string().date(),
  check_out_date: z.string().date(),
  actual_check_in_at: z.string().datetime().nullable(),
  actual_check_out_at: z.string().datetime().nullable(),
  adults: z.number().int().min(1),
  children: z.number().int().min(0),
  special_requests: z.string().nullable(),
  internal_notes: z.string().nullable(),
  created_by: z.string().uuid().nullable(),
});
export type Stay = z.infer<typeof StaySchema>;

export const CreateStaySchema = StaySchema.omit({
  id: true,
  organisation_id: true,
  created_at: true,
  updated_at: true,
  actual_check_in_at: true,
  actual_check_out_at: true,
  created_by: true,
});
export type CreateStay = z.infer<typeof CreateStaySchema>;

// ---------------------------------------------------------------------------
// Service / Treatment
// ---------------------------------------------------------------------------

export const ServiceSchema = BaseEntitySchema.extend({
  name: z.string().min(1).max(255),
  description: z.string().nullable(),
  category: z.string().nullable(),
  duration_minutes: z.number().int().min(1),
  buffer_minutes: z.number().int().min(0),
  base_price: z.number().positive().nullable(),
  currency: z.string().length(3).nullable(),
  requires_room: z.boolean(),
  max_group_size: z.number().int().min(1),
  is_active: z.boolean(),
  notion_page_id: z.string().nullable(),
});
export type Service = z.infer<typeof ServiceSchema>;

// ---------------------------------------------------------------------------
// Appointment
// ---------------------------------------------------------------------------

export const AppointmentSchema = BaseEntitySchema.extend({
  guest_id: z.string().uuid(),
  stay_id: z.string().uuid().nullable(),
  service_id: z.string().uuid(),
  practitioner_id: z.string().uuid().nullable(),
  room_id: z.string().uuid().nullable(),
  status: z.nativeEnum(AppointmentStatus),
  scheduled_start_at: z.string().datetime(),
  scheduled_end_at: z.string().datetime(),
  actual_start_at: z.string().datetime().nullable(),
  actual_end_at: z.string().datetime().nullable(),
  notes: z.string().nullable(),
  billable_event_id: z.string().uuid().nullable(),
  created_by: z.string().uuid().nullable(),
});
export type Appointment = z.infer<typeof AppointmentSchema>;

// ---------------------------------------------------------------------------
// Package
// ---------------------------------------------------------------------------

export const PackageInclusionSchema = z.object({
  id: z.string().uuid(),
  package_id: z.string().uuid(),
  service_id: z.string().uuid(),
  quantity: z.number().int().min(1),
  notes: z.string().nullable(),
});
export type PackageInclusion = z.infer<typeof PackageInclusionSchema>;

export const PackageSchema = BaseEntitySchema.extend({
  name: z.string().min(1).max(255),
  description: z.string().nullable(),
  duration_nights: z.number().int().nullable(),
  price: z.number().positive(),
  currency: z.string().length(3),
  is_active: z.boolean(),
  inclusions: z.array(PackageInclusionSchema).optional(),
});
export type Package = z.infer<typeof PackageSchema>;

// ---------------------------------------------------------------------------
// Billable Event
// ---------------------------------------------------------------------------

export const BillableEventSchema = BaseEntitySchema.extend({
  guest_id: z.string().uuid(),
  stay_id: z.string().uuid().nullable(),
  appointment_id: z.string().uuid().nullable(),
  service_id: z.string().uuid().nullable(),
  event_type: z.nativeEnum(BillableEventType),
  description: z.string().min(1),
  quantity: z.number().positive(),
  unit_price: z.number().nonnegative(),
  currency: z.string().length(3),
  is_included_in_package: z.boolean(),
  package_assignment_id: z.string().uuid().nullable(),
  approval_status: z.nativeEnum(ApprovalStatus),
  approved_by: z.string().uuid().nullable(),
  approved_at: z.string().datetime().nullable(),
  idempotency_key: z.string().min(1),
  occurred_at: z.string().datetime(),
});
export type BillableEvent = z.infer<typeof BillableEventSchema>;

// ---------------------------------------------------------------------------
// Invoice
// ---------------------------------------------------------------------------

export const InvoiceLineItemSchema = z.object({
  id: z.string().uuid(),
  invoice_id: z.string().uuid(),
  billable_event_id: z.string().uuid().nullable(),
  description: z.string(),
  quantity: z.number().positive(),
  unit_price: z.number().nonnegative(),
  subtotal: z.number().nonnegative(),
  tax_rate: z.number().min(0).max(1),
  tax_amount: z.number().nonnegative(),
  total: z.number().nonnegative(),
  sort_order: z.number().int(),
});
export type InvoiceLineItem = z.infer<typeof InvoiceLineItemSchema>;

export const InvoiceSchema = BaseEntitySchema.extend({
  guest_id: z.string().uuid(),
  stay_id: z.string().uuid().nullable(),
  invoice_number: z.string(),
  status: z.nativeEnum(InvoiceStatus),
  subtotal: z.number().nonnegative(),
  tax_amount: z.number().nonnegative(),
  total_amount: z.number().nonnegative(),
  currency: z.string().length(3),
  due_date: z.string().date().nullable(),
  notes: z.string().nullable(),
  sent_at: z.string().datetime().nullable(),
  paid_at: z.string().datetime().nullable(),
  stripe_invoice_id: z.string().nullable(),
  line_items: z.array(InvoiceLineItemSchema).optional(),
});
export type Invoice = z.infer<typeof InvoiceSchema>;

// ---------------------------------------------------------------------------
// Knowledge Chunk
// ---------------------------------------------------------------------------

export const KnowledgeChunkSchema = z.object({
  id: z.string().uuid(),
  organisation_id: z.string().uuid(),
  source_type: z.enum(['notion_page', 'uploaded_doc', 'manual_entry']),
  source_id: z.string(),
  source_url: z.string().url().nullable(),
  page_title: z.string(),
  section_heading: z.string().nullable(),
  content_text: z.string(),
  content_hash: z.string(),
  token_count: z.number().int().nullable(),
  metadata: z.record(z.unknown()),
  last_indexed_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
});
export type KnowledgeChunk = z.infer<typeof KnowledgeChunkSchema>;
