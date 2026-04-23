# Make Scenarios

These scenarios are owned by the Operations team and edited in Make (formerly Integromat).
This directory contains exported scenario blueprints for version control.

## Active Scenarios

### 01 — Booking Confirmation Sequence
- **Trigger**: Supabase webhook `booking.confirmed` event received
- **Steps**:
  1. Fetch full booking details from Supabase
  2. Send confirmation email via SendGrid (template: `booking-confirmed`)
  3. Create Google Calendar event for guest
  4. Schedule WhatsApp reminder 48h before check-in (Twilio)
  5. Log notification in Supabase `comms.notification_log`
- **Owner**: Operations Manager
- **Editable by**: Any Make team member
- **Blueprint file**: `booking-confirmation.json`

### 02 — Post-Stay Follow-Up Sequence
- **Trigger**: Supabase webhook `booking.checked_out` event
- **Steps**:
  1. Wait 2 hours post checkout (Make delay module)
  2. Send thank-you email with review link (SendGrid)
  3. Wait 7 days
  4. Send follow-up programme offer email
  5. If email opens within 48h: trigger Slack alert to sales team
- **Owner**: Marketing Lead
- **Blueprint file**: `post-stay-followup.json`

### 03 — Pre-Arrival Checklist
- **Trigger**: 3 days before `check_in_date` (Make scheduler)
- **Steps**:
  1. Fetch upcoming arrivals from Supabase
  2. For each arrival: send pre-arrival information email
  3. Post summary to Slack `#front-desk-today`
- **Owner**: Front Desk Lead

## Exporting Scenarios

To export a scenario for version control:
1. Open the scenario in Make
2. Click "..." → Export blueprint
3. Save the JSON file to this directory
4. Commit with description of what changed

## Important

Make scenarios should never access clinical data endpoints.
All Supabase writes go through Edge Functions, never direct database URLs.
API keys stored in Make should be minimum-permission service accounts.
