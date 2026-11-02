# Validation record

## Passed

- 21 Django integration tests using the explicitly selected SQLite test configuration.
- Order creation, server-calculated prices, immutable catalogue snapshots, phone normalization, session-bound checkout tokens and idempotent retries.
- CSRF rejection, unknown/inactive catalogue rejection, form bounds, honeypot rejection and shared database rate limiting.
- Fake/oversized image rejection, upload metadata removal, protected receipts/design images and permission-gated payment proofs.
- Prepaid payment requirements and pending verification; the disabled gateway never reports payment success.
- Review moderation, approved-only rating statistics, exclusion of demo testimonials, escaped review text and rating validation.
- Order tracking with matching phone, status-only responses, Explore filters and HTMX fragments, admin shipping guard, public route rendering and health response.
- `manage.py check`: no issues.
- `manage.py makemigrations --check --dry-run`: no missing migrations.
- Production WhiteNoise `collectstatic`: hashed/compressed asset generation completed successfully.
- `gunicorn config.wsgi:application --check-config`: successful.
- `node --check studio/static/studio/app.js` and `sh -n entrypoint.sh`: successful.
- Both Compose files parse as YAML, each declaring three services.
- Desktop browser checks of color selection, print choice, back placement, scale changes and reveal using actual rendered Django templates.
- Narrow viewport browser checks using a 390px iframe: mobile wardrobe, four-card print deck, reveal, successful PNG-export UI response and checkout recap rendered. This is a viewport simulation, not a physical-phone test.

## Security deployment check

`manage.py check --deploy` was run with debug off, a generated environment secret, HTTPS redirection and secure cookies. It returned no errors and two deliberate initial-deployment warnings: `security.W005` (HSTS include-subdomains) and `security.W021` (HSTS preload). These are explicit opt-ins in `.env.example`; the README explains enabling them only after domain-wide HTTPS is established.

## Verification limits

- Docker Engine/Compose and a running PostgreSQL server were unavailable in the execution workspace. Container startup, PostgreSQL-specific concurrency, and the live TLS Nginx path were not executed. The README includes the commands to run the tests against the Docker PostgreSQL service.
- The managed browser preview runtime did not contain Django. Browser visual/interaction checks used a static snapshot rendered from the real templates and local demo media. Server submissions were verified by Django integration tests rather than by that browser snapshot.
- Live payment transfer, real gateway verification, Instagram account behavior and physical garment/print matching were not tested. QR payments deliberately require manual verification; the gateway adapter is explicitly disabled.
- Native Web Share depends on the browser/device. PNG download is the implemented fallback; a native mobile share sheet was not exercised here.
- No claim of a formal accessibility audit or load/security certification is made. Keyboard controls, visible focus, contrast-conscious palettes, labels, reduced motion and glass fallbacks are implemented.

## Runtime asset budget

The authored application JS is approximately 8.2 KB gzip. GSAP, HTMX and Alpine add approximately 60.7 KB gzip combined. The app stylesheet is approximately 8.5 KB gzip before final formatting, which does not materially change compressed size. Fonts are self-hosted (Inter Latin about 48 KB; Noto Sans Devanagari about 121 KB). Catalogue images are generated locally by the seed command and lazily loaded where appropriate. No runtime CDN or Instagram request is required by the designer.
