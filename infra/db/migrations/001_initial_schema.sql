-- =============================================================================
-- Migration: 001_initial_schema
-- Description: Full initial schema for AI Operations Platform
-- Date: 2026-04-23
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- SCHEMAS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS guests;
CREATE SCHEMA IF NOT EXISTS bookings;
CREATE SCHEMA IF NOT EXISTS scheduling;
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS comms;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- =============================================================================
-- ENUMERATIONS
-- =============================================================================

CREATE TYPE public.user_role AS ENUM (
  'super_admin', 'org_admin', 'manager',
  'front_desk', 'practitioner', 'nurse',
  'finance', 'read_only'
);

CREATE TYPE crm.lead_source AS ENUM (
  'web_form', 'email', 'whatsapp', 'phone',
  'referral', 'walk_in', 'social_media', 'partner', 'other'
);

CREATE TYPE crm.lead_status AS ENUM (
  'new', 'contacted', 'qualified',
  'proposal_sent', 'converted', 'closed_lost', 'on_hold'
);

CREATE TYPE bookings.stay_status AS ENUM (
  'enquiry', 'confirmed', 'checked_in',
  'checked_out', 'cancelled', 'no_show'
);

CREATE TYPE scheduling.appointment_status AS ENUM (
  'scheduled', 'confirmed', 'in_progress',
  'completed', 'cancelled', 'no_show', 'rescheduled'
);

CREATE TYPE billing.event_type AS ENUM (
  'treatment', 'product_sale', 'room_charge',
  'extra_service', 'penalty', 'adjustment', 'deposit'
);

CREATE TYPE billing.approval_status AS ENUM (
  'pending', 'approved', 'waived', 'disputed'
);

CREATE TYPE billing.invoice_status AS ENUM (
  'draft', 'sent', 'paid', 'partially_paid', 'voided', 'refunded'
);

CREATE TYPE knowledge.source_type AS ENUM (
  'notion_page', 'uploaded_doc', 'manual_entry'
);

CREATE TYPE knowledge.ingestion_status AS ENUM (
  'pending', 'running', 'completed', 'failed', 'skipped'
);

CREATE TYPE public.outbox_status AS ENUM (
  'pending', 'processing', 'processed', 'failed', 'dead_lettered'
);

-- =============================================================================
-- TENANCY
-- =============================================================================

CREATE TABLE public.organisations (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name            TEXT NOT NULL,
  slug            TEXT NOT NULL UNIQUE,
  plan            TEXT NOT NULL DEFAULT 'standard',
  settings        JSONB NOT NULL DEFAULT '{}',
  timezone        TEXT NOT NULL DEFAULT 'UTC',
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- USERS (extends auth.users)
-- =============================================================================

CREATE TABLE public.users (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  role            public.user_role NOT NULL DEFAULT 'read_only',
  full_name       TEXT NOT NULL,
  avatar_url      TEXT,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_seen_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX users_org_idx ON public.users(organisation_id);
CREATE INDEX users_role_idx ON public.users(organisation_id, role);

-- =============================================================================
-- GUEST PROFILES
-- =============================================================================

CREATE TABLE guests.guests (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id       UUID NOT NULL REFERENCES public.organisations(id),
  external_id           TEXT,
  first_name            TEXT NOT NULL,
  last_name             TEXT NOT NULL,
  -- encrypted PII stored as bytea; decrypted at application layer
  email_encrypted       BYTEA,
  phone_encrypted       BYTEA,
  dob_encrypted         BYTEA,
  nationality           CHAR(2),
  preferred_language    CHAR(5) DEFAULT 'en',
  gender                TEXT,
  referral_source       TEXT,
  tags                  TEXT[] DEFAULT '{}',
  internal_notes        TEXT,
  gdpr_consented_at     TIMESTAMPTZ,
  marketing_consent     BOOLEAN NOT NULL DEFAULT FALSE,
  is_vip                BOOLEAN NOT NULL DEFAULT FALSE,
  profile_completeness  SMALLINT NOT NULL DEFAULT 0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organisation_id, external_id)
);

CREATE INDEX guests_org_idx ON guests.guests(organisation_id);
CREATE INDEX guests_created_idx ON guests.guests(organisation_id, created_at DESC);

-- =============================================================================
-- CRM / LEADS
-- =============================================================================

CREATE TABLE crm.leads (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id     UUID NOT NULL REFERENCES public.organisations(id),
  guest_id            UUID REFERENCES guests.guests(id),
  source              crm.lead_source NOT NULL DEFAULT 'other',
  status              crm.lead_status NOT NULL DEFAULT 'new',
  inquiry_text        TEXT,
  preferred_programme TEXT,
  preferred_dates     DATERANGE,
  budget_indicator    TEXT,
  inquiry_date        DATE NOT NULL DEFAULT CURRENT_DATE,
  assigned_to         UUID REFERENCES public.users(id),
  last_contacted_at   TIMESTAMPTZ,
  follow_up_at        TIMESTAMPTZ,
  converted_at        TIMESTAMPTZ,
  closed_at           TIMESTAMPTZ,
  close_reason        TEXT,
  ai_summary          TEXT,
  ai_suggested_action TEXT,
  metadata            JSONB NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX leads_org_status_idx ON crm.leads(organisation_id, status);
CREATE INDEX leads_assigned_idx ON crm.leads(assigned_to);
CREATE INDEX leads_follow_up_idx ON crm.leads(follow_up_at) WHERE follow_up_at IS NOT NULL;

-- =============================================================================
-- SERVICE CATALOGUE
-- =============================================================================

CREATE TABLE scheduling.services (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  name              TEXT NOT NULL,
  description       TEXT,
  category          TEXT,
  duration_minutes  SMALLINT NOT NULL,
  buffer_minutes    SMALLINT NOT NULL DEFAULT 0,
  base_price        NUMERIC(10, 2),
  currency          CHAR(3),
  requires_room     BOOLEAN NOT NULL DEFAULT FALSE,
  max_group_size    SMALLINT NOT NULL DEFAULT 1,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  notion_page_id    TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX services_org_idx ON scheduling.services(organisation_id);

-- =============================================================================
-- PROGRAMMES
-- =============================================================================

CREATE TABLE scheduling.programmes (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  name            TEXT NOT NULL,
  description     TEXT,
  duration_nights SMALLINT NOT NULL,
  base_price      NUMERIC(10, 2),
  currency        CHAR(3),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- ROOMS / RESOURCES
-- =============================================================================

CREATE TABLE bookings.rooms (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  name            TEXT NOT NULL,
  room_type       TEXT NOT NULL,
  capacity        SMALLINT NOT NULL DEFAULT 1,
  floor           TEXT,
  amenities       TEXT[] DEFAULT '{}',
  is_accommodation BOOLEAN NOT NULL DEFAULT FALSE,
  is_treatment    BOOLEAN NOT NULL DEFAULT FALSE,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX rooms_org_idx ON bookings.rooms(organisation_id);

-- =============================================================================
-- STAYS (ACCOMMODATION BOOKINGS)
-- =============================================================================

CREATE TABLE bookings.stays (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id       UUID NOT NULL REFERENCES public.organisations(id),
  guest_id              UUID NOT NULL REFERENCES guests.guests(id),
  room_id               UUID REFERENCES bookings.rooms(id),
  programme_id          UUID REFERENCES scheduling.programmes(id),
  status                bookings.stay_status NOT NULL DEFAULT 'enquiry',
  check_in_date         DATE NOT NULL,
  check_out_date        DATE NOT NULL,
  actual_check_in_at    TIMESTAMPTZ,
  actual_check_out_at   TIMESTAMPTZ,
  adults                SMALLINT NOT NULL DEFAULT 1,
  children              SMALLINT NOT NULL DEFAULT 0,
  special_requests      TEXT,
  internal_notes        TEXT,
  created_by            UUID REFERENCES public.users(id),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_dates CHECK (check_out_date > check_in_date)
);

CREATE INDEX stays_org_guest_idx ON bookings.stays(organisation_id, guest_id);
CREATE INDEX stays_dates_idx ON bookings.stays(organisation_id, check_in_date, check_out_date);
CREATE INDEX stays_status_idx ON bookings.stays(organisation_id, status);

-- =============================================================================
-- PRACTITIONERS
-- =============================================================================

CREATE TABLE scheduling.practitioners (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  user_id           UUID REFERENCES public.users(id),
  full_name         TEXT NOT NULL,
  specialisations   TEXT[] DEFAULT '{}',
  bio               TEXT,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX practitioners_org_idx ON scheduling.practitioners(organisation_id);

CREATE TABLE scheduling.practitioner_services (
  practitioner_id UUID NOT NULL REFERENCES scheduling.practitioners(id),
  service_id      UUID NOT NULL REFERENCES scheduling.services(id),
  PRIMARY KEY (practitioner_id, service_id)
);

-- =============================================================================
-- APPOINTMENTS
-- =============================================================================

CREATE TABLE scheduling.appointments (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id       UUID NOT NULL REFERENCES public.organisations(id),
  guest_id              UUID NOT NULL REFERENCES guests.guests(id),
  stay_id               UUID REFERENCES bookings.stays(id),
  service_id            UUID NOT NULL REFERENCES scheduling.services(id),
  practitioner_id       UUID REFERENCES scheduling.practitioners(id),
  room_id               UUID REFERENCES bookings.rooms(id),
  status                scheduling.appointment_status NOT NULL DEFAULT 'scheduled',
  scheduled_start_at    TIMESTAMPTZ NOT NULL,
  scheduled_end_at      TIMESTAMPTZ NOT NULL,
  actual_start_at       TIMESTAMPTZ,
  actual_end_at         TIMESTAMPTZ,
  notes                 TEXT,
  billable_event_id     UUID,
  created_by            UUID REFERENCES public.users(id),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valid_schedule CHECK (scheduled_end_at > scheduled_start_at)
);

CREATE INDEX appointments_org_time_idx ON scheduling.appointments(organisation_id, scheduled_start_at);
CREATE INDEX appointments_guest_idx ON scheduling.appointments(guest_id);
CREATE INDEX appointments_practitioner_idx ON scheduling.appointments(practitioner_id, scheduled_start_at);
CREATE INDEX appointments_status_idx ON scheduling.appointments(organisation_id, status);

-- =============================================================================
-- CLINICAL RECORDS
-- =============================================================================

CREATE TABLE clinical.health_assessments (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  guest_id          UUID NOT NULL REFERENCES guests.guests(id),
  stay_id           UUID REFERENCES bookings.stays(id),
  assessed_by       UUID REFERENCES public.users(id),
  assessment_type   TEXT NOT NULL,
  findings          TEXT,
  contraindications TEXT[] DEFAULT '{}',
  recommendations   TEXT,
  attachments       TEXT[] DEFAULT '{}',
  assessed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX health_assessments_guest_idx ON clinical.health_assessments(guest_id);

CREATE TABLE clinical.treatment_notes (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  appointment_id  UUID NOT NULL REFERENCES scheduling.appointments(id),
  practitioner_id UUID NOT NULL REFERENCES scheduling.practitioners(id),
  guest_id        UUID NOT NULL REFERENCES guests.guests(id),
  content         TEXT NOT NULL,
  is_ai_assisted  BOOLEAN NOT NULL DEFAULT FALSE,
  ai_draft_used   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX treatment_notes_appointment_idx ON clinical.treatment_notes(appointment_id);
CREATE INDEX treatment_notes_guest_idx ON clinical.treatment_notes(guest_id);

-- =============================================================================
-- BILLING
-- =============================================================================

CREATE TABLE billing.packages (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  name              TEXT NOT NULL,
  description       TEXT,
  duration_nights   SMALLINT,
  price             NUMERIC(10, 2) NOT NULL,
  currency          CHAR(3) NOT NULL,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE billing.package_inclusions (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  package_id  UUID NOT NULL REFERENCES billing.packages(id) ON DELETE CASCADE,
  service_id  UUID NOT NULL REFERENCES scheduling.services(id),
  quantity    SMALLINT NOT NULL DEFAULT 1,
  notes       TEXT,
  UNIQUE (package_id, service_id)
);

CREATE TABLE billing.package_assignments (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id       UUID NOT NULL REFERENCES public.organisations(id),
  guest_id              UUID NOT NULL REFERENCES guests.guests(id),
  stay_id               UUID REFERENCES bookings.stays(id),
  package_id            UUID NOT NULL REFERENCES billing.packages(id),
  inclusions_snapshot   JSONB NOT NULL,
  price_at_assignment   NUMERIC(10, 2) NOT NULL,
  currency              CHAR(3) NOT NULL,
  started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX package_assignments_guest_idx ON billing.package_assignments(guest_id);
CREATE INDEX package_assignments_stay_idx ON billing.package_assignments(stay_id);

CREATE TABLE billing.billable_events (
  id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id         UUID NOT NULL REFERENCES public.organisations(id),
  guest_id                UUID NOT NULL REFERENCES guests.guests(id),
  stay_id                 UUID REFERENCES bookings.stays(id),
  appointment_id          UUID REFERENCES scheduling.appointments(id),
  service_id              UUID REFERENCES scheduling.services(id),
  event_type              billing.event_type NOT NULL,
  description             TEXT NOT NULL,
  quantity                NUMERIC(8, 2) NOT NULL DEFAULT 1,
  unit_price              NUMERIC(10, 2) NOT NULL,
  currency                CHAR(3) NOT NULL,
  is_included_in_package  BOOLEAN NOT NULL DEFAULT FALSE,
  package_assignment_id   UUID REFERENCES billing.package_assignments(id),
  approval_status         billing.approval_status NOT NULL DEFAULT 'pending',
  approved_by             UUID REFERENCES public.users(id),
  approved_at             TIMESTAMPTZ,
  idempotency_key         TEXT NOT NULL UNIQUE,
  occurred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX billable_events_guest_idx ON billing.billable_events(guest_id);
CREATE INDEX billable_events_stay_idx ON billing.billable_events(stay_id);
CREATE INDEX billable_events_approval_idx ON billing.billable_events(organisation_id, approval_status);

CREATE TABLE billing.invoices (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  guest_id          UUID NOT NULL REFERENCES guests.guests(id),
  stay_id           UUID REFERENCES bookings.stays(id),
  invoice_number    TEXT NOT NULL UNIQUE,
  status            billing.invoice_status NOT NULL DEFAULT 'draft',
  subtotal          NUMERIC(10, 2) NOT NULL DEFAULT 0,
  tax_amount        NUMERIC(10, 2) NOT NULL DEFAULT 0,
  total_amount      NUMERIC(10, 2) NOT NULL DEFAULT 0,
  currency          CHAR(3) NOT NULL,
  due_date          DATE,
  notes             TEXT,
  sent_at           TIMESTAMPTZ,
  paid_at           TIMESTAMPTZ,
  voided_at         TIMESTAMPTZ,
  stripe_invoice_id TEXT,
  created_by        UUID REFERENCES public.users(id),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE billing.invoice_line_items (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  invoice_id        UUID NOT NULL REFERENCES billing.invoices(id) ON DELETE CASCADE,
  billable_event_id UUID REFERENCES billing.billable_events(id),
  description       TEXT NOT NULL,
  quantity          NUMERIC(8, 2) NOT NULL DEFAULT 1,
  unit_price        NUMERIC(10, 2) NOT NULL,
  subtotal          NUMERIC(10, 2) NOT NULL,
  tax_rate          NUMERIC(5, 4) NOT NULL DEFAULT 0,
  tax_amount        NUMERIC(10, 2) NOT NULL DEFAULT 0,
  total             NUMERIC(10, 2) NOT NULL,
  sort_order        SMALLINT NOT NULL DEFAULT 0
);

CREATE INDEX invoice_line_items_invoice_idx ON billing.invoice_line_items(invoice_id);

-- =============================================================================
-- COMMUNICATIONS
-- =============================================================================

CREATE TABLE comms.notification_log (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  guest_id        UUID REFERENCES guests.guests(id),
  user_id         UUID REFERENCES public.users(id),
  channel         TEXT NOT NULL,
  template_key    TEXT,
  subject         TEXT,
  body_preview    TEXT,
  status          TEXT NOT NULL DEFAULT 'queued',
  external_id     TEXT,
  sent_at         TIMESTAMPTZ,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX notification_log_org_idx ON comms.notification_log(organisation_id, created_at DESC);

-- =============================================================================
-- KNOWLEDGE BASE (VECTOR)
-- =============================================================================

CREATE TABLE knowledge.chunks (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  source_type       knowledge.source_type NOT NULL,
  source_id         TEXT NOT NULL,
  source_url        TEXT,
  page_title        TEXT NOT NULL,
  section_heading   TEXT,
  content_text      TEXT NOT NULL,
  content_hash      TEXT NOT NULL,
  embedding         vector(1536),
  token_count       SMALLINT,
  metadata          JSONB NOT NULL DEFAULT '{}',
  last_indexed_at   TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organisation_id, source_id, content_hash)
);

CREATE INDEX knowledge_chunks_org_idx ON knowledge.chunks(organisation_id);
CREATE INDEX knowledge_chunks_source_idx ON knowledge.chunks(organisation_id, source_type, source_id);

-- IVFFlat index for approximate nearest neighbour search
-- Adjust lists parameter based on dataset size: lists ≈ sqrt(row_count)
CREATE INDEX knowledge_chunks_embedding_idx
  ON knowledge.chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE TABLE knowledge.ingestion_jobs (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  source_type       knowledge.source_type NOT NULL,
  source_id         TEXT NOT NULL,
  source_url        TEXT,
  status            knowledge.ingestion_status NOT NULL DEFAULT 'pending',
  pages_processed   INT NOT NULL DEFAULT 0,
  chunks_upserted   INT NOT NULL DEFAULT 0,
  error_message     TEXT,
  triggered_by      TEXT,
  started_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- AI COPILOT LOG
-- =============================================================================

CREATE TABLE public.ai_interactions (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id   UUID NOT NULL REFERENCES public.organisations(id),
  user_id           UUID REFERENCES public.users(id),
  guest_id          UUID REFERENCES guests.guests(id),
  interaction_type  TEXT NOT NULL,
  prompt_preview    TEXT,
  response_preview  TEXT,
  model             TEXT NOT NULL,
  input_tokens      INT,
  output_tokens     INT,
  latency_ms        INT,
  retrieved_chunks  INT,
  accepted_by_user  BOOLEAN,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ai_interactions_org_idx ON public.ai_interactions(organisation_id, created_at DESC);

-- =============================================================================
-- TRANSACTIONAL OUTBOX
-- =============================================================================

CREATE TABLE public.outbox_events (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organisation_id UUID NOT NULL REFERENCES public.organisations(id),
  event_type      TEXT NOT NULL,
  aggregate_type  TEXT NOT NULL,
  aggregate_id    UUID NOT NULL,
  payload         JSONB NOT NULL,
  version         TEXT NOT NULL DEFAULT '1',
  status          public.outbox_status NOT NULL DEFAULT 'pending',
  attempts        SMALLINT NOT NULL DEFAULT 0,
  last_error      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at    TIMESTAMPTZ
);

CREATE INDEX outbox_pending_idx ON public.outbox_events(status, created_at)
  WHERE status = 'pending';
CREATE INDEX outbox_aggregate_idx ON public.outbox_events(aggregate_type, aggregate_id);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TABLE audit.log (
  id              BIGSERIAL PRIMARY KEY,
  organisation_id UUID,
  table_name      TEXT NOT NULL,
  record_id       UUID,
  operation       TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
  old_values      JSONB,
  new_values      JSONB,
  changed_by      UUID,
  changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address      INET,
  user_agent      TEXT,
  trace_id        TEXT
) PARTITION BY RANGE (changed_at);

-- Create initial quarterly partitions
CREATE TABLE audit.log_2026_q1 PARTITION OF audit.log
  FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
CREATE TABLE audit.log_2026_q2 PARTITION OF audit.log
  FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
CREATE TABLE audit.log_2026_q3 PARTITION OF audit.log
  FOR VALUES FROM ('2026-07-01') TO ('2026-10-01');
CREATE TABLE audit.log_2026_q4 PARTITION OF audit.log
  FOR VALUES FROM ('2026-10-01') TO ('2027-01-01');

CREATE INDEX audit_log_table_record_idx ON audit.log(table_name, record_id);
CREATE INDEX audit_log_changed_by_idx ON audit.log(changed_by);
CREATE INDEX audit_log_org_idx ON audit.log(organisation_id, changed_at DESC);

-- =============================================================================
-- AUDIT TRIGGER FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION audit.log_change()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit.log (
    organisation_id, table_name, record_id, operation,
    old_values, new_values, changed_by, trace_id
  ) VALUES (
    COALESCE(
      (NEW.organisation_id)::uuid,
      (OLD.organisation_id)::uuid
    ),
    TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
    COALESCE((NEW.id)::uuid, (OLD.id)::uuid),
    TG_OP,
    CASE WHEN TG_OP != 'INSERT' THEN to_jsonb(OLD) ELSE NULL END,
    CASE WHEN TG_OP != 'DELETE' THEN to_jsonb(NEW) ELSE NULL END,
    current_setting('app.current_user_id', true)::uuid,
    current_setting('app.trace_id', true)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to key tables
CREATE TRIGGER audit_guests
  AFTER INSERT OR UPDATE OR DELETE ON guests.guests
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_stays
  AFTER INSERT OR UPDATE OR DELETE ON bookings.stays
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_appointments
  AFTER INSERT OR UPDATE OR DELETE ON scheduling.appointments
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_billable_events
  AFTER INSERT OR UPDATE OR DELETE ON billing.billable_events
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_invoices
  AFTER INSERT OR UPDATE OR DELETE ON billing.invoices
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_package_assignments
  AFTER INSERT OR UPDATE OR DELETE ON billing.package_assignments
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

-- Enable RLS on all multi-tenant tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE guests.guests ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings.stays ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduling.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical.health_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical.treatment_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.billable_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbox_events ENABLE ROW LEVEL SECURITY;

-- Organisation isolation policy (applied to all tables via this pattern)
CREATE POLICY org_isolation ON guests.guests
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON crm.leads
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON bookings.stays
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON scheduling.appointments
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON billing.billable_events
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON billing.invoices
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

CREATE POLICY org_isolation ON knowledge.chunks
  USING (organisation_id = (current_setting('app.organisation_id', true))::uuid);

-- Clinical data: restricted to clinical roles only
CREATE POLICY clinical_role_access ON clinical.health_assessments
  USING (
    organisation_id = (current_setting('app.organisation_id', true))::uuid
    AND current_setting('app.role', true) IN ('org_admin', 'manager', 'nurse', 'practitioner')
  );

CREATE POLICY clinical_role_access ON clinical.treatment_notes
  USING (
    organisation_id = (current_setting('app.organisation_id', true))::uuid
    AND current_setting('app.role', true) IN ('org_admin', 'manager', 'nurse', 'practitioner')
  );

-- =============================================================================
-- ANALYTICS VIEWS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE VIEW analytics.daily_utilisation AS
SELECT
  a.organisation_id,
  DATE(a.scheduled_start_at) AS date,
  r.id AS room_id,
  r.name AS room_name,
  COUNT(*) FILTER (WHERE a.status = 'completed') AS completed_sessions,
  COUNT(*) FILTER (WHERE a.status IN ('scheduled', 'confirmed', 'in_progress')) AS upcoming_sessions,
  COUNT(*) FILTER (WHERE a.status = 'no_show') AS no_shows,
  SUM(EXTRACT(EPOCH FROM (a.scheduled_end_at - a.scheduled_start_at)) / 3600)
    FILTER (WHERE a.status = 'completed') AS billed_hours
FROM scheduling.appointments a
LEFT JOIN bookings.rooms r ON a.room_id = r.id
GROUP BY 1, 2, 3, 4;

CREATE VIEW analytics.billing_summary AS
SELECT
  be.organisation_id,
  DATE_TRUNC('month', be.occurred_at) AS month,
  COUNT(DISTINCT be.guest_id) AS unique_guests,
  SUM(be.unit_price * be.quantity) FILTER (WHERE NOT be.is_included_in_package) AS extra_revenue,
  SUM(be.unit_price * be.quantity) AS total_billable_value,
  AVG(be.unit_price * be.quantity) FILTER (WHERE NOT be.is_included_in_package) AS avg_extra_per_event
FROM billing.billable_events be
WHERE be.approval_status = 'approved'
GROUP BY 1, 2;

-- =============================================================================
-- UPDATED_AT TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.organisations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON guests.guests
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON crm.leads
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON bookings.stays
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON scheduling.appointments
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON billing.invoices
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
