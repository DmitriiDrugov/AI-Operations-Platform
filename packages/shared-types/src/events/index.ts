import { z } from 'zod';

// ---------------------------------------------------------------------------
// Domain events published to the outbox and consumed by workers/lambdas
// Each event is versioned; consumers must tolerate unknown fields
// ---------------------------------------------------------------------------

const BaseEventSchema = z.object({
  id: z.string().uuid(),
  version: z.literal('1'),
  organisation_id: z.string().uuid(),
  occurred_at: z.string().datetime(),
  metadata: z
    .object({
      source_service: z.string().optional(),
      trace_id: z.string().optional(),
      user_id: z.string().uuid().optional(),
    })
    .optional(),
});

// ---------------------------------------------------------------------------
// Lead events
// ---------------------------------------------------------------------------

export const LeadCreatedEventSchema = BaseEventSchema.extend({
  event_type: z.literal('lead.created'),
  aggregate_type: z.literal('lead'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    lead_id: z.string().uuid(),
    guest_name: z.string().nullable(),
    source: z.string(),
    inquiry_text: z.string().nullable(),
    inquiry_date: z.string().date(),
  }),
});
export type LeadCreatedEvent = z.infer<typeof LeadCreatedEventSchema>;

export const LeadConvertedEventSchema = BaseEventSchema.extend({
  event_type: z.literal('lead.converted'),
  aggregate_type: z.literal('lead'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    lead_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    stay_id: z.string().uuid().nullable(),
    converted_at: z.string().datetime(),
  }),
});
export type LeadConvertedEvent = z.infer<typeof LeadConvertedEventSchema>;

// ---------------------------------------------------------------------------
// Booking / Stay events
// ---------------------------------------------------------------------------

export const BookingConfirmedEventSchema = BaseEventSchema.extend({
  event_type: z.literal('booking.confirmed'),
  aggregate_type: z.literal('stay'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    stay_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    guest_name: z.string(),
    guest_email: z.string().email().nullable(),
    check_in_date: z.string().date(),
    check_out_date: z.string().date(),
    programme_name: z.string().nullable(),
    room_name: z.string().nullable(),
  }),
});
export type BookingConfirmedEvent = z.infer<typeof BookingConfirmedEventSchema>;

export const GuestCheckedInEventSchema = BaseEventSchema.extend({
  event_type: z.literal('booking.checked_in'),
  aggregate_type: z.literal('stay'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    stay_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    guest_name: z.string(),
    room_name: z.string().nullable(),
    checked_in_at: z.string().datetime(),
  }),
});
export type GuestCheckedInEvent = z.infer<typeof GuestCheckedInEventSchema>;

export const GuestCheckedOutEventSchema = BaseEventSchema.extend({
  event_type: z.literal('booking.checked_out'),
  aggregate_type: z.literal('stay'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    stay_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    guest_name: z.string(),
    guest_email: z.string().email().nullable(),
    checked_out_at: z.string().datetime(),
    invoice_id: z.string().uuid().nullable(),
  }),
});
export type GuestCheckedOutEvent = z.infer<typeof GuestCheckedOutEventSchema>;

// ---------------------------------------------------------------------------
// Appointment events
// ---------------------------------------------------------------------------

export const AppointmentCompletedEventSchema = BaseEventSchema.extend({
  event_type: z.literal('appointment.completed'),
  aggregate_type: z.literal('appointment'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    appointment_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    stay_id: z.string().uuid().nullable(),
    service_id: z.string().uuid(),
    service_name: z.string(),
    practitioner_id: z.string().uuid().nullable(),
    completed_at: z.string().datetime(),
  }),
});
export type AppointmentCompletedEvent = z.infer<
  typeof AppointmentCompletedEventSchema
>;

// ---------------------------------------------------------------------------
// Billing events
// ---------------------------------------------------------------------------

export const BillableEventCreatedSchema = BaseEventSchema.extend({
  event_type: z.literal('billable_event.created'),
  aggregate_type: z.literal('billable_event'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    billable_event_id: z.string().uuid(),
    guest_id: z.string().uuid(),
    stay_id: z.string().uuid().nullable(),
    description: z.string(),
    amount: z.number(),
    currency: z.string(),
    is_included_in_package: z.boolean(),
  }),
});
export type BillableEventCreated = z.infer<typeof BillableEventCreatedSchema>;

export const InvoiceSentEventSchema = BaseEventSchema.extend({
  event_type: z.literal('invoice.sent'),
  aggregate_type: z.literal('invoice'),
  aggregate_id: z.string().uuid(),
  payload: z.object({
    invoice_id: z.string().uuid(),
    invoice_number: z.string(),
    guest_id: z.string().uuid(),
    guest_email: z.string().email().nullable(),
    total_amount: z.number(),
    currency: z.string(),
    due_date: z.string().date().nullable(),
  }),
});
export type InvoiceSentEvent = z.infer<typeof InvoiceSentEventSchema>;

// ---------------------------------------------------------------------------
// Union type for all domain events
// ---------------------------------------------------------------------------

export type DomainEvent =
  | LeadCreatedEvent
  | LeadConvertedEvent
  | BookingConfirmedEvent
  | GuestCheckedInEvent
  | GuestCheckedOutEvent
  | AppointmentCompletedEvent
  | BillableEventCreated
  | InvoiceSentEvent;
