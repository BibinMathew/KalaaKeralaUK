# Kalaa Kerala — Git-ready community website

A portable Django application for Kalaa Kerala Arts & Sports Club, Ashfield & Mansfield, UK. This is a separate, Git-deployable version of the earlier prototype. It does not depend on ChatGPT hosting or ChatGPT login.

## Included

- Original responsive Kalaa Kerala design using the supplied logo.
- Home, About, Office Bearers, Contact and community initiative sections.
- Month calendar with previous/next navigation, category/search filters, upcoming/past events, event detail pages and downloadable `.ics` calendars.
- Single designated administrator, password login, login throttling and Django CSRF/session protection.
- Event creation, UK dates/times, draft/publish controls, free registration and GBP payments.
- Photo albums, multi-image upload, captions, lightbox, image compression and EXIF removal.
- YouTube/Vimeo video gallery, loaded only after a visitor chooses Play.
- Learning Zone, Newcomers Guide and Useful Links, managed in the admin.
- On-site membership applications, optional membership application fee, separate approval status and CSV export.
- Stored contact enquiries with optional notification to the club.
- Stripe hosted Checkout, server-controlled amounts, signed webhook verification, idempotent payment confirmation, expiration/failure and refund state handling.
- GitHub CI, pinned dependencies, initial database migrations, Dockerfile and a PostgreSQL/Caddy Docker Compose deployment.

## Run on your Mac

Python 3.12 is the tested version. Run these commands inside this extracted folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a
source .env
set +a
python manage.py migrate
python manage.py seed_content
python manage.py createsuperuser --username clubadmin
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/admin/`.

The app reads environment variables. It does **not** automatically load `.env`; use the shell commands above, Docker Compose, or your hosting dashboard. If running at 127.0.0.1 instead of localhost, set SITE_URL accordingly when testing Stripe redirects.

Optional local demo calendar:

```sh
python manage.py seed_content --demo
```

Demo events are prominently marked DEMO, have bookings disabled and are blocked from seeding with DEBUG=false. Do not seed demo content in a production database. No committee names, real future dates, prices or event photos are invented.

## Upload to Git

Create an empty private repository in your Git provider. Then:

```sh
git init
git branch -M main
git add .
git commit -m "Initial Kalaa Kerala community website"
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

Replace `YOUR_REPOSITORY_URL`. The included `.gitignore` excludes secrets, databases and uploaded media. Keep hosting, database, Stripe and domain accounts under club ownership. Source is separate from operational data: backing up Git does not back up members or photos.

## Build and deploy from Git

Use a host that supports Python/Docker applications with persistent data. This application is **not** a static GitHub Pages site and cannot be deployed as static HTML alone.

- Docker build: `docker build -t kalaa-kerala .`
- Hosted build command: `sh scripts/build.sh`
- Hosted start command: `sh scripts/start.sh`
- Required environment: SECRET_KEY, DEBUG=false, SITE_URL, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, ADMIN_USERNAME, DATABASE_URL; plus media storage and Stripe settings.

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for full setup, including your existing domain, PostgreSQL, durable images and HTTPS. See **[docs/STRIPE.md](docs/STRIPE.md)** for payments.

## Admin setup

1. Sign in as the single account named in ADMIN_USERNAME (default `clubadmin`). No public user registration is provided.
2. Edit **Club settings**: contact details, description, optional homepage photograph, membership terms, privacy notice and refund terms.
3. Add confirmed office bearers, events, albums, videos and resources. Draft content stays private.
4. Open an album, save it, then use **Upload multiple photos**. Up to 20 photos per batch, max 10 MB each, max 25 megapixels. Browser previews do not upload anything until submitted.
5. Configure and test Stripe, then enable **payments_enabled**. Set event prices and **booking_open** separately.
6. Confirm membership terms/privacy and enable **membership_open**. A fee of zero accepts applications without payment. Paid applications remain pending review until the admin approves them.
7. Set **contact_open** after completing the privacy notice. Enquiries remain stored even if email delivery fails.

Payments, contact submissions and memberships are deliberately closed initially until the club completes its configuration. Admin creation is manual; no password or payment secret is shipped.

## Checks

```sh
python manage.py test club
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING  # production environment
```

See [docs/TESTING.md](docs/TESTING.md) for test evidence and remaining live checks.

## Current scope and honest limitations

- Each event has one admission price, quantity 1–10. Multiple ticket tiers, seat capacity, waiting lists, QR check-in, recurring memberships and member self-service accounts are not included.
- Membership applications are handled by the club, with optional one-time fee. The site does not automatically renew memberships.
- Stripe sends payment receipts when configured in Stripe. Automatic custom ticket emails are not included.
- Admin approval is recorded in the dashboard; communicating approval/decline is currently the club's responsibility.
- Refunds are initiated in Stripe, not from this site. Webhooks synchronise refund status.
- No reference-site photographs, committee data, contact details or source code have been copied.
- Default privacy/refund/membership wording must be completed by the club before launch. These are configurable drafts, not legal advice.
- This source package has automated test coverage; live Stripe, domain, email, browser/device and hosting acceptance checks remain before production sign-off.

## Documentation

- [Reference review and feature mapping](docs/REFERENCE-REVIEW.md)
- [Architecture and data flows](docs/ARCHITECTURE.md)
- [Deployment and backups](docs/DEPLOYMENT.md)
- [Stripe setup](docs/STRIPE.md)
- [Testing and launch checklist](docs/TESTING.md)
- [Agent development rules](AGENTS.md)

## Free client review deployment

Use the included `render.yaml` with Supabase PostgreSQL and private photo storage. Follow [the Render + Supabase guide](docs/RENDER-SUPABASE.md). This requires your GitHub, Render and Supabase accounts; no live deployment or credentials are included.
