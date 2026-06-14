# Vibe questionnaire — trigger specification (§4.2)

This file is the contract between the backend scheduler and the questionnaire;
it documents *when* the form fires (no code here).

## Trigger condition
1. The app detects a **phone-number exchange** in the chat between two users
   (the conventional signal that a real meeting is likely).
2. Wait a **buffer delay** (a few days) to let the date actually happen.
3. Send a **smartphone notification** asking the user to fill the Vibe form.

## Notification copy (Hebrew)
> "איך היה הדייט? ספר/י לנו ב-30 שניות ונדייק לך את ההמלצות 💛"

## Design constraints
- The form must be **short and fast** to maximize response rate (target ≥ 60%,
  KPI #4) and avoid drop-off.
- The link carries `?user=`, `?api=` and `?profile=` query params so the saved
  record links the scraped dry features to the reported outcome.

## Open items
- Exact detection of phone-number exchange depends on each app; in the pilot it
  may be simulated or self-reported via the extension.
