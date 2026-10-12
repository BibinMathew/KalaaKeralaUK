# Deploy from Git

## Option A: Docker Compose on your server

Prerequisites: a Linux server with Docker Compose, your existing domain pointed at its IP, ports 80/443 open, and persistent disks. The server must have enough disk capacity for photos and backups.

1. Clone the repository and copy `.env.example` to `.env`.
2. Generate a secret: `python3 -c 'import secrets; print(secrets.token_urlsafe(64))'`. Set SECRET_KEY to that value privately.
3. Add DOMAIN (hostname only, no https/path) and POSTGRES_PASSWORD. Use a randomly generated hexadecimal password so it is URL-safe in DATABASE_URL.
4. Set DEBUG=false. Configure Stripe and email as needed. Keep ADMIN_USERNAME=clubadmin or choose a specific account name.
5. Run `docker compose up -d --build`.
6. Create the single administrator: `docker compose exec web python manage.py createsuperuser --username clubadmin`.
7. Visit your domain over HTTPS and `/admin/`. Caddy obtains HTTPS certificates when DNS is correct. Run `docker compose exec web python manage.py check --deploy --fail-level WARNING`.
8. Complete the launch checklist before accepting payments.

The database and media are separate persistent volumes. Caddy serves only public image files from the media volume; it never executes them. The application re-encodes uploaded images as JPEG. Do not place private documents in media. PostgreSQL has no published host port. The application is reachable only through Caddy. TRUST_PROXY_HTTPS is true here because Caddy is the trusted proxy.

## Option B: a Git-connected Python/Docker host

Connect your own repository in the hosting dashboard. Use the Dockerfile, or build `sh scripts/build.sh` and start `sh scripts/start.sh` on Python 3.12. The internal application port is 8000; configure the host's routing accordingly.

Set:

- DEBUG=false; a random SECRET_KEY.
- SITE_URL=https://your-domain.co.uk (canonical origin).
- ALLOWED_HOSTS=your-domain.co.uk (comma-separated if multiple).
- CSRF_TRUSTED_ORIGINS=https://your-domain.co.uk.
- DATABASE_URL for a durable PostgreSQL database.
- ADMIN_USERNAME for the designated admin.
- TRUST_PROXY_HTTPS=true only if the hosting proxy strips/replaces incoming X-Forwarded-Proto. Otherwise configure trusted TLS handling before using it.
- S3-compatible storage settings in `.env.example` for ephemeral hosts. The implementation uses signed image URLs, so the bucket need not be public. Keep the bucket private and grant the app only necessary bucket access. Configure lifecycle/retention and backups.
- SMTP and Stripe values as described in their guides.

Without S3, you need a persistent media disk and a web-server route for `/media/`; Django's development media serving is disabled in production. An ephemeral filesystem will lose uploads. Git does not store uploaded photos or the database.

This package does not provision external accounts or buy hosting. GitHub Pages/static hosting is unsuitable for the Python backend.

## Updates

Deploy staging first. Run CI, review changes, take a backup, then pull/build your selected commit. This starter runs migrations at startup; use a single application replica during migrations. For larger deployments, move migration execution into one release job. Do not blindly roll back database migrations: prefer backwards-compatible schema changes and a separately tested data recovery plan.

## Backups and recovery

Back up PostgreSQL and media daily to separate storage with an agreed retention period. For Compose, a database backup can be generated with:

```sh
mkdir -p backups
docker compose exec -T db pg_dump -U kalaa kalaa > backups/kalaa.sql
```

Media backup: copy `/app/media` from the running web container into a protected backup location, or use your storage provider's versioning/backup capability. Avoid committing either backup to Git. Encrypt backups and restrict access. Test restoring the database and photographs into a separate staging deployment before signing off production.

Schedule `python manage.py clearsessions`, `python manage.py cleanup_records`, and `python manage.py axes_reset_logs` as appropriate for retention. Inspect the installed command's help before selecting an Axes retention period. Monitor application errors and webhook failures. An HTTP GET `/health/` checks the process, not database or Stripe health; use separate dependency monitoring.

## Administrator recovery

`python manage.py changepassword clubadmin` resets the admin password interactively. `python manage.py axes_reset` clears lockouts; use only after investigating failed login attempts. There is no default password, no public registration and no email password-reset flow in this starter. For account rotation, create the replacement locally, update ADMIN_USERNAME, disable the old account and re-test access. Add MFA/SSO or an access gateway if required by the club's security policy.
