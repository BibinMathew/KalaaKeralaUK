# Architecture

One Django application, server-rendered templates and a small amount of browser JavaScript. PostgreSQL is the production database; SQLite is for local development. Uploaded JPEGs live in a durable volume or S3-compatible storage. Stripe hosts the payment form; card numbers never reach this application.

## Responsibilities

- `club/models.py`: data structure and image normalisation.
- `club/forms.py`: bounded user input, consent and spam honeypot.
- `club/views.py`: public pages, calendar, membership, enquiries and booking orchestration.
- `club/payments.py`: checkout and webhook handling.
- `club/admin.py`: single-admin restriction, content publishing and exports.
- `config/settings.py`: environment-specific settings.
- `templates/` and `static/club/`: public UI and small enhancements.

## Payment flow

A server-validated form creates a pending Order with a session-scoped checkout token. Price is read from the database and converted to integer GBP pence. Repeat submissions reuse the order. The Stripe SDK creates a hosted Checkout Session with an idempotency key. A signed Stripe webhook retrieves the session from Stripe, checks amount/currency/mode/session identity, locks the order and records payment once. The return page only reads status; it cannot confirm payment. Order confirmation requires the initiating browser session. Refunds are initiated in Stripe.

## Content and permissions

Only the configured ADMIN_USERNAME, active and superuser, can access the admin. Other staff/superuser names are denied. Account management is intentionally not exposed through the club admin; operators create or recover the one account using Django commands. Membership applicants do not create login accounts. Draft content is excluded from public queries. Photos belong to albums; publish only photos the club can share.

## Operational boundaries

Membership and payment state are separate. A paid application is not automatically approved. Notifications are a convenience; database records are authoritative. Session/CSRF cookies use secure flags under production settings. Login protection uses database-backed Django Axes. Public form limits use database counters, not in-memory process counters. Counters use a hash of the remote address, not a stored raw address. Configure edge rate limits and trusted proxy behaviour before public launch.

Storage deletes currently remove database records, not necessarily the underlying storage objects. Review and purge orphaned objects on your retention schedule, including backups. This conservative behaviour avoids accidental photo loss but means deleting an album is not a complete privacy erasure. Use the storage administration process to fulfil erasure requests.
