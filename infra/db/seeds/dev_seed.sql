-- =============================================================================
-- Development seed data — NOT for production
-- Run after migrations to populate local dev environment with test fixtures
-- =============================================================================

-- Test organisation
INSERT INTO public.organisations (id, name, slug, timezone, currency)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'Serenity Wellness Retreat', 'serenity', 'Europe/London', 'GBP'),
  ('00000000-0000-0000-0000-000000000002', 'Vitality Medical Spa', 'vitality', 'America/New_York', 'USD')
ON CONFLICT DO NOTHING;

-- Services
INSERT INTO scheduling.services (id, organisation_id, name, category, duration_minutes, buffer_minutes, base_price, currency, requires_room)
VALUES
  (uuid_generate_v4(), '00000000-0000-0000-0000-000000000001', 'Swedish Massage 60 min', 'Massage', 60, 15, 120.00, 'GBP', TRUE),
  (uuid_generate_v4(), '00000000-0000-0000-0000-000000000001', 'Deep Tissue Massage 90 min', 'Massage', 90, 15, 160.00, 'GBP', TRUE),
  (uuid_generate_v4(), '00000000-0000-0000-0000-000000000001', 'Morning Yoga Class', 'Group Class', 60, 0, 25.00, 'GBP', TRUE),
  (uuid_generate_v4(), '00000000-0000-0000-0000-000000000001', 'Nutritional Consultation', 'Consultation', 45, 15, 90.00, 'GBP', FALSE),
  (uuid_generate_v4(), '00000000-0000-0000-0000-000000000001', 'Infrared Sauna Session', 'Thermal', 30, 10, 40.00, 'GBP', TRUE)
ON CONFLICT DO NOTHING;

-- Packages
INSERT INTO billing.packages (id, organisation_id, name, description, duration_nights, price, currency)
VALUES
  (
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    '7-Day Detox Retreat',
    'Complete 7-night wellness programme with daily treatments',
    7,
    2800.00,
    'GBP'
  ),
  (
    '10000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Weekend Recharge',
    '2-night stress relief programme',
    2,
    650.00,
    'GBP'
  )
ON CONFLICT DO NOTHING;

-- Rooms
INSERT INTO bookings.rooms (organisation_id, name, room_type, capacity, is_accommodation, is_treatment)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'Room 1 - Meadow View', 'deluxe', 1, TRUE, FALSE),
  ('00000000-0000-0000-0000-000000000001', 'Room 2 - Garden View', 'standard', 1, TRUE, FALSE),
  ('00000000-0000-0000-0000-000000000001', 'Treatment Room A', 'treatment', 1, FALSE, TRUE),
  ('00000000-0000-0000-0000-000000000001', 'Treatment Room B', 'treatment', 1, FALSE, TRUE),
  ('00000000-0000-0000-0000-000000000001', 'Yoga Studio', 'group', 20, FALSE, TRUE)
ON CONFLICT DO NOTHING;
