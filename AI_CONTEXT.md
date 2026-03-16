# AI Context: MCOT Equipment Service (Updated)

This file is a practical handoff note for the next AI pass.

## Project Snapshot

- Name: MCOT Equipment Service
- Stack: Django 4.2, Python 3.9, django-allauth, Tailwind via CDN, Alpine.js
- Main domain: equipment/studio/package booking, quotation flow, payment confirmation
- Cart source of truth: localStorage key `mcot_cart`

## Current Truth (March 2026)

### Booking/Backend Status

- The previous checkout crash (`No Product matches the given query`) was addressed.
- Missing/stale cart item IDs now return a user-facing conflict/validation response instead of a system-level crash.
- Package booking behavior was changed to allow standalone package booking even when no `PackageItem` rows exist.
- Regression tests were added for:
  - missing product ID handling
  - empty package booking success

### Frontend/Theming Status

- Dark mode coverage has been expanded across auth pages and key customer-facing pages.
- Mobile-first policy is now the default expectation for UI changes.
- Additional responsive fixes were applied to reduce overlap/overflow on mobile, especially around:
  - hero blocks
  - sticky bars/nav
  - fixed bottom action bars
  - long text wrapping in auth forms

### Repository Hygiene Status

- Removed unneeded local artifacts and migration leftovers from git tracking.
- Files removed from index (kept locally where needed):
  - `.vscode/settings.json`
  - `db.sqlite3`
  - `db_mock.sqlite3`
  - `deploy_to_vps.sh`
- Unused root clutter was cleaned (e.g., temporary markdown/presentation/package files from prior migration context).

## Important Working Rules

1. Treat this repo as mobile-first by default.
2. Prevent regression when touching booking or auth flows.
3. Do not re-track local DB/editor artifacts.
4. Keep UI edits consistent with current dark/light design language.

## Key Files (High Impact)

- `apps/store/views/booking.py`
- `apps/store/services/booking_service.py`
- `apps/store/services/availability.py`
- `templates/base.html`
- `templates/booking/*`
- `templates/store/*`
- `templates/account/*` and `templates/registration/*`

## Quick Validation Commands

- `python3 manage.py check`
- `python3 manage.py test apps.store.tests_auth -v 1`

## Deployment to VPS (How-to)

- Deployment is typically handled via `bash deploy_to_vps.sh` from the project root.
- **Process**: The script commits local code, pushes it to the `v2` branch, and establishes an SSH session (`43.173.251.244` on port `8022`) to pull the code, install requirements, migrate, and collect static files automatically on the VPS.
- **Manual Actions**: If the background server needs a restart, you may need to SSH into the VPS and restart the `nohup python3 manage.py runserver 0.0.0.0:8000 &` process or system daemon manually, since the script only handles code sync and migrations.
- Do not run the deployment blindly; always check stability locally with tests and mock DB.

## Notes for Next AI Pass

- Assume there may be many modified files in a dirty worktree; never reset unrelated user work.
- If user asks for more cleanup, run `git ls-files -ci --exclude-standard` first to find tracked files that should be ignored.
- Prioritize bug-risk review first, visual polish second.
