# Working on Kalaa Kerala

- Keep changes scoped to one feature or defect. Do not rewrite unrelated modules.
- Describe the acceptance criteria before implementing a new feature.
- Preserve server-side admin authorisation, CSRF, rate limits, image validation and payment verification.
- Never mark an order paid from a browser return URL or client-provided amount.
- Do not weaken or delete failing tests to obtain a passing result. Explain changes to test expectations.
- Add a regression test for security, payment or data-integrity fixes.
- Keep migration history immutable after deployment; add migrations for schema changes.
- Add dependencies only when justified. Pin and review them; never add a custom auth/cryptography layer where the framework already provides it.
- Do not include secrets, production data, uploaded media or backups in Git.
- Use Stripe test mode and synthetic members for development.
- Do not invent club names, officers, dates, activities or photos.
- Production deployment and destructive data changes require the operator's explicit approval.
- Before handover run tests, migration checks and production deployment checks; report checks not performed.
