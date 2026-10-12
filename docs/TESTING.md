# Verification and launch checklist

## Executed for this package

- 32 Django automated tests passed on Python 3.12 with SQLite test isolation.
- Public routes rendered successfully, including populated albums, video/committee/resource pages.
- Calendar leap-year handling, invalid months and category filtering passed.
- Draft event protection, closed/past booking rejection and anonymous admin restrictions passed.
- Only the designated superuser can access admin; other superusers are denied.
- CSRF rejection, honeypot and persistent form rate-limit checks passed.
- Free and paid membership/event flows tested. Repeated free booking/application submissions create one record.
- Server-side pricing verified with an attempted browser price override.
- Forged payment return URLs cannot mark orders paid.
- Real signature construction/verification tested for webhooks; Stripe API responses mocked.
- Duplicate webhook delivery, amount mismatch, unpaid checkout, refunds and refund-before-completion tested.
- JPEG/PNG decoding, upload validation, re-encoding/resizing and batch admin uploads passed.
- Safe CSV export and calendar newline escaping checked.
- `collectstatic` completed, including hashed/compressed assets.
- `makemigrations --check --dry-run`: no pending model changes.
- `check --deploy --fail-level WARNING` passed under production-style environment settings.

## Not executed here

- Live Stripe test-mode checkout: requires the club's account keys and webhook endpoint.
- Browser-based desktop/mobile inspection of this local Python app: the available cloud browser is separate from the local project environment. Server-rendered responses were tested, but that is not a substitute for browser interaction/visual checks.
- Docker image/Compose runtime: Docker is unavailable in this build environment. Docker and Compose definitions are supplied, not represented as runtime-tested.
- PostgreSQL integration/concurrent payment delivery: the supplied GitHub workflow runs the test suite against PostgreSQL when pushed. That workflow has not run in your repository yet.
- Actual domain DNS/HTTPS, SMTP delivery, S3 credentials or backup restoration.

## Required before public launch

1. Run the GitHub workflow against PostgreSQL and resolve any failures.
2. Deploy staging from a selected commit; run migrations and production checks.
3. Create the designated admin. Check valid login, invalid login/lockout, logout, password recovery command and access denial for other accounts.
4. Replace draft privacy/refund/membership terms and contact information. Decide retention periods and who handles data requests.
5. Add real content. Delete any demo events. Check unpublished entries remain hidden.
6. On Safari/iPhone and Chrome/desktop: navigation, mobile menu, calendar navigation/search, event details, .ics import, forms, album lightbox keyboard close, video play and admin upload.
7. Test Stripe success, declined card, cancellation, duplicate webhook delivery and refund using test mode. Verify database status against Stripe. Enable Stripe receipt emails if needed.
8. Test a membership application with and without a fee. Verify admin approval is separate from payment.
9. Test email notification delivery and confirm submissions are still stored if SMTP is unavailable.
10. Deploy a replacement build and confirm photos and records persist.
11. Restore a backup into staging. Set up error and webhook monitoring and a contact for incidents.
12. Configure live Stripe secrets, recheck the endpoint, then enable payments/booking/membership as appropriate.

This is an implementation and source handover, not a claim that production acceptance has already been completed.
