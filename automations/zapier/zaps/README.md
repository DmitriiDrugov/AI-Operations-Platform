# Zapier Zaps

These zaps are owned by the Operations team and managed in the Zapier workspace.
Engineers maintain this directory as documentation only — actual zap configuration lives in Zapier.

## Active Zaps

### 01 — Typeform Lead Intake
- **Trigger**: New Typeform submission (Inquiry Form)
- **Action**: POST to `{SUPABASE_URL}/functions/v1/inbound-webhook`
- **Headers**: `x-webhook-source: typeform`, `x-webhook-secret: {SECRET}`
- **Field mapping**: `name → first_name + last_name`, `email → email`, `message → inquiry_text`, `programme_interest → preferred_programme`
- **Owner**: Operations Manager
- **Last tested**: 2026-04-23

### 02 — Google Calendar → Booking Sync
- **Trigger**: New event created in "Wellness Bookings" Google Calendar
- **Action**: POST to Supabase Edge Function to create or update appointment
- **Note**: One-directional only; platform → calendar sync is handled by Make
- **Owner**: Operations Manager

### 03 — Gmail Lead Capture
- **Trigger**: New email matching label "Booking Inquiry"
- **Action**: POST to Edge Function `inbound-webhook` with `source: email`
- **Filter**: Email must contain inquiry keywords (configured in Zapier filter)
- **Owner**: Front Desk Lead

### 04 — Slack Notification: New VIP Guest
- **Trigger**: Supabase webhook when `guests.is_vip = true` set on a new guest
- **Action**: Post to Slack `#vip-arrivals` channel
- **Owner**: Operations Manager

## Adding a New Zap

1. Create the zap in the Zapier workspace
2. Document it in this file with: trigger, action, field mapping, owner
3. Test with a real event before marking active
4. All zaps that write to Supabase must use the Edge Function endpoints (never write directly to DB)
