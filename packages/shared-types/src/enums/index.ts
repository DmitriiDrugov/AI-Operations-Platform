export const UserRole = {
  SUPER_ADMIN: 'super_admin',
  ORG_ADMIN: 'org_admin',
  MANAGER: 'manager',
  FRONT_DESK: 'front_desk',
  PRACTITIONER: 'practitioner',
  NURSE: 'nurse',
  FINANCE: 'finance',
  READ_ONLY: 'read_only',
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const LeadSource = {
  WEB_FORM: 'web_form',
  EMAIL: 'email',
  WHATSAPP: 'whatsapp',
  PHONE: 'phone',
  REFERRAL: 'referral',
  WALK_IN: 'walk_in',
  SOCIAL_MEDIA: 'social_media',
  PARTNER: 'partner',
  OTHER: 'other',
} as const;
export type LeadSource = (typeof LeadSource)[keyof typeof LeadSource];

export const LeadStatus = {
  NEW: 'new',
  CONTACTED: 'contacted',
  QUALIFIED: 'qualified',
  PROPOSAL_SENT: 'proposal_sent',
  CONVERTED: 'converted',
  CLOSED_LOST: 'closed_lost',
  ON_HOLD: 'on_hold',
} as const;
export type LeadStatus = (typeof LeadStatus)[keyof typeof LeadStatus];

export const StayStatus = {
  ENQUIRY: 'enquiry',
  CONFIRMED: 'confirmed',
  CHECKED_IN: 'checked_in',
  CHECKED_OUT: 'checked_out',
  CANCELLED: 'cancelled',
  NO_SHOW: 'no_show',
} as const;
export type StayStatus = (typeof StayStatus)[keyof typeof StayStatus];

export const AppointmentStatus = {
  SCHEDULED: 'scheduled',
  CONFIRMED: 'confirmed',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  NO_SHOW: 'no_show',
  RESCHEDULED: 'rescheduled',
} as const;
export type AppointmentStatus =
  (typeof AppointmentStatus)[keyof typeof AppointmentStatus];

export const BillableEventType = {
  TREATMENT: 'treatment',
  PRODUCT_SALE: 'product_sale',
  ROOM_CHARGE: 'room_charge',
  EXTRA_SERVICE: 'extra_service',
  PENALTY: 'penalty',
  ADJUSTMENT: 'adjustment',
  DEPOSIT: 'deposit',
} as const;
export type BillableEventType =
  (typeof BillableEventType)[keyof typeof BillableEventType];

export const ApprovalStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  WAIVED: 'waived',
  DISPUTED: 'disputed',
} as const;
export type ApprovalStatus =
  (typeof ApprovalStatus)[keyof typeof ApprovalStatus];

export const InvoiceStatus = {
  DRAFT: 'draft',
  SENT: 'sent',
  PAID: 'paid',
  PARTIALLY_PAID: 'partially_paid',
  VOIDED: 'voided',
  REFUNDED: 'refunded',
} as const;
export type InvoiceStatus = (typeof InvoiceStatus)[keyof typeof InvoiceStatus];

export const InteractionType = {
  GENERAL: 'general',
  GUEST_SUMMARY: 'guest_summary',
  SOP_LOOKUP: 'sop_lookup',
  BILLING_QUERY: 'billing_query',
  DRAFT_MESSAGE: 'draft_message',
  CLINICAL_SUMMARY: 'clinical_summary',
} as const;
export type InteractionType =
  (typeof InteractionType)[keyof typeof InteractionType];
