# BABAL WEARS — Make it yours

A complete Django 5.2 + PostgreSQL custom T-shirt studio. Django templates, HTMX, Alpine.js, GSAP and a shared canvas renderer power the experience. No SPA framework, Node build step, Instagram scraping, gateway credentials, real payment account or fabricated customer testimonials are included.

## 1. Brand analysis (assumptions)

The supplied Instagram profile and highlight links could not be fetched. No brand screenshots were supplied with this request. The following are creative assumptions, not observations of BABAL WEARS' actual identity:

| Area | Working assumption |
| --- | --- |
| Voice | Playful, self-aware, direct, with light Nepali/Roman-Nepali accents. |
| Audience | Mobile-first Nepali customers interested in expressive everyday streetwear. |
| Identity | A temporary typographic `babal*` wordmark, warm paper, ink, acidic lime and small coral/cobalt accents. |
| T-shirts | Five placeholder colors: Washed black, Chalk, Moss, Lilac, Burnt orange. |
| Prints | Four original demo artworks: Offline club, Low battery, Own lane, Waveform. These are not Instagram highlight designs. |
| Pricing | Demo base price NPR 1,200, delivery NPR 150, sizes S–XXL. Print/color surcharges default to zero. |
| Other products | Illustrative crewneck, cap, tote and hoodie. Every demo product and price is marked. |
| Payments | COD works immediately. Pay First appears when an admin enables actual payment details. |
| Delivery | Availability and timing are confirmed manually. No specific delivery area or delivery-time promise is invented. |

The tiny woven diamond band is an original geometric reference to Dhaka weaving, not an authenticated textile pattern or a claimed brand asset. No mountains, flags, temples or unrelated cultural symbols are used as decoration.

## 2. Style guide

| Token | Value | Role |
| --- | --- | --- |
| Ink | `#17191B` | Main text, primary buttons, rules |
| Paper | `#F4F1E8` | Main canvas |
| Electric lime | `#D5FF45` | Stickers, typographic interruptions, active accents |
| Cobalt | `#375CFF` | Focus rings, artwork |
| Coral | `#FF785D` | Secondary stickers and artwork |
| Lilac | `#C8BCF2` | Accent surfaces and artwork |
| Muted text | `#555952` | Supporting copy |

Inter variable is the main grotesque; Noto Sans Devanagari handles Nepali. Both are self-hosted WOFF2 files with bundled OFL licenses. Font stacks retain system fallbacks. The base UI scale is 12 / 14 / 16 / 24 / 40 / 72 / 120px, with fluid display headings up to 140px and compact editorial metadata. Content uses a 12-column desktop grid, an 8px spacing rhythm, and 20px mobile page gutters. Desktop columns collapse to one on small screens.

```css
:root {
  --glass-bg: rgba(255, 255, 249, .72);
  --glass-border: rgba(255, 255, 255, .85);
  --glass-shadow: 0 12px 40px rgba(28, 32, 25, .07);
  --glass-blur: 20px;
  --radius: 18px;
}
```

Glass has an opaque fallback. Foreground copy uses dark ink or muted dark text over pale surfaces, and cream over dark buttons. Focus rings are visible. Motion respects `prefers-reduced-motion`. The wardrobe also supports arrow keys, Home/End, swatches and explicit previous/next buttons.

### Five signature interactions

1. **The flowing rail:** pointer drag, touch swipe and wheel movement with velocity-based momentum, center selection and GSAP elastic hanger sway. At rail boundaries, vertical wheel movement returns to page scrolling.
2. **Color as atmosphere:** the background tint morphs with the focused garment; selecting a shirt lifts it from the rail and settles it into the print stage.
3. **The sticker deck:** slightly fanned cards lift into focus; choosing art immediately redraws the canvas. Chest, center and back views share one renderer, with 60–140% scale controls.
4. **The reveal:** a short GSAP spin leads to a final tee. Export produces a 1000×1200 PNG with a view/placement label; Web Share is used where supported and falls back to download.
5. **The numbered journey:** the persistent 01–05 control tracks progress; the final receipt contains an order ID, saved design, price recap, status and Instagram DM link.

## 3. Architecture

| Layer | Responsibility |
| --- | --- |
| Nginx, unprivileged | Entry point, 12 MB request limit, public media, trusted forwarding headers |
| Gunicorn, non-root | Two workers × two threads, WSGI request handling |
| Django + WhiteNoise | Templates, forms, CSRF, static asset compression, admin, order creation and authorization |
| PostgreSQL 16 | Catalogue, configuration, orders, moderation, sessions and shared rate-limit buckets |
| Public media volume | Sanitized print/product/review images and brand-uploaded payment QR images |
| Private media volume | Order design PNGs and payment screenshots; no public media mapping |
| HTMX | Explore category filtering and review-form submission, with ordinary form fallbacks |
| Alpine.js | Payment timing/provider panel state |
| GSAP + vanilla JS | Rail physics, step transitions, reveal, canvas composition, checkout submission |

`studio/services.py` prices orders from database records within a transaction. The browser cannot set price, payment verification or order status. A session-bound submission key makes retries return the same order. Order metadata snapshots preserve color/print names and totals when catalogue entries change.

The generated image is a visual reference only. Staff should use the recorded color, print, placement and scale when preparing production. The server cannot prove that a client-supplied preview matches the selection. This implementation does not claim photorealistic production dimensions or calibrated garment colors.

Payment proofs are readable only by staff with the `view_paymentproof` permission. Design previews and receipts require the purchasing browser session or `view_order` permission. Tracking requires both order ID and normalized phone and reveals status only, not the address or uploaded files.

See `docs/FILE_TREE.txt` for the complete file tree, and `docs/FULL_SOURCE.md` for all text source files organized by path. Font binaries are included in the ZIP. The implementation is split in logical order: settings, models/validation/services, views/URLs/admin, templates, CSS/JS, Docker/deployment, tests and documentation.

## 4. Start the demo

Requires Docker Engine/Desktop and Docker Compose **2.24 or newer** (the Compose file uses an optional `.env` file).

From this directory:

```bash
docker compose up --build
```

Open <http://localhost:8000>. On first boot the entrypoint waits for PostgreSQL, applies the included migrations, collects static files and seeds the demo catalogue. It generates a random session key if none is supplied. No superuser is pre-created and no default admin password exists.

In another terminal:

```bash
docker compose exec web python manage.py createsuperuser
```

Open <http://localhost:8000/admin/>. Stop the demo with `docker compose down`; named volumes remain. Do not use `down -v` unless you intend to delete the database and uploaded files.

### Keep development sessions across restarts

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the generated value into `DJANGO_SECRET_KEY` in `.env`, then recreate the web container. Keep `.env` private. The demo intentionally uses PostgreSQL trust authentication only on the unpublished Docker network and binds Nginx to `127.0.0.1`. The production override requires a password and a separate fresh database volume. Never expose the demo database or treat demo settings as production configuration.

### Local Python development without Docker

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export USE_SQLITE=1
export DJANGO_DEBUG=1
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

This explicit SQLite mode is for local development and fast tests. To use PostgreSQL locally, remove `USE_SQLITE` and export `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. On Windows use PowerShell environment syntax or Docker Desktop/WSL. Never use `runserver` as a production server.

## 5. Run the actual customer journey

1. Drag/swipe the rail or tap a swatch, then choose **That's my color**.
2. Pick an admin-uploaded print, placement and scale. Back placement changes the mockup to a back view.
3. Reveal the tee. Save its PNG or share through the device's share sheet. File sharing needs a supported browser and secure context; an ordinary PNG download is the fallback.
4. Fill name, optional Instagram handle, Nepal mobile, province, district, municipality, ward, landmark, size, quantity and optional notes. Choose COD, or an enabled prepaid provider and screenshot.
5. Submit. The final PNG and selected options are saved with the order, and you receive an order ID and recap.

The form accepts Devanagari digits, spaces and an optional +977 prefix for a mobile number. It checks the format `9[678]` followed by eight digits. It does not verify SIM ownership or whether the number is reachable. District and municipality are free text; province is selected from the seven provinces and ward is constrained to 1–35. Quantity is 1–20. Confirm regional delivery eligibility operationally.

Only design options are saved in browser local storage; personal details and proofs are not. Reopening the studio starts at step 01 with the last design selection. The final receipt is available in the same browser session; the independent `/track/` page works with order ID + phone.

## 6. Manage the brand in admin

### Colors and prints

- **T-shirt colors:** add the actual name and six-digit hex value, optional price adjustment and sorting order. Deactivate unavailable colors instead of deleting entries referenced by orders.
- **Prints:** add approved art, name, short description and optional surcharge. Transparent PNG is best. Crop unnecessary transparent margins before uploading, because the canvas fits the complete uploaded image bounds. JPEG and WebP are also accepted.
- All image uploads are limited to 5 MB and 16 megapixels, with a 6000px side limit. They are decoded, stripped of metadata and normalized to PNG, at a maximum 1800px side. SVG and GIF uploads are rejected.
- Upload the actual Instagram highlight artwork manually with permission. The application never scrapes Instagram.
- Deactivate the four demo prints once the real catalogue is ready; leave `is_demo` checked for any examples you retain.

### Other products

Open **Products**, upload a product image, name/category/description/price, and optionally paste an HTTPS Instagram post link. Set `is_active` to publish it. Explore always offers **Order via DM**; it shows **See on Instagram** only when a real post URL is configured. Demo illustrations do not claim to depict actual stock.

### Prices, sizing and delivery

Open **Store settings** to edit the base tee price, flat delivery fee, contact phone, delivery note and size guidance. Unit price is base + color adjustment + print surcharge. The delivery fee is charged once per order, independent of quantity. This is a flat-fee implementation, not a zone-based shipping engine. Size choices live in `studio/models.py` as `SIZE_CHOICES`; add/edit choices and create a migration if your range differs. Sizing copy is visible beside checkout.

### Reviews

New submissions are unapproved. In **Reviews**, inspect the text/photo and use **Approve selected reviews**. **Unpublish** removes them from the public wall. Only approved, non-demo reviews contribute to average rating and count. There are no seeded fake testimonials.

### Orders and payment review

Use list filters for status, payment status, method, province, size and date; search by order number, name, mobile or Instagram handle. Open an order to inspect the saved design and its private payment proof. Review the proof against your provider's actual transaction record, then use **Mark paid after manually checking payment**. The action records reviewer and time. **Reject selected payment proofs** records a rejected status. Add context in the proof's admin note and contact the customer through your normal process.

**Mark eligible orders shipped** skips unverified prepaid orders and cancelled/delivered orders. COD orders are eligible without prepaid verification. Use the order form's status field for confirmed, printing, delivered or cancelled states. Bulk actions write Django admin audit log entries.

Grant staff the appropriate view/change permissions. A staff flag alone does not give access to private proofs. Use a superuser for initial setup only, then give operational staff the minimum permissions they need.

## 7. Add actual payment details

In **Payment options**, add one record for eSewa, Khalti or FonePay. Enter the real account display name, number and/or upload the merchant payment QR. Add customer instructions and enable the record. The active provider appears under **Pay first**; the uploaded proof becomes mandatory. At least a QR image or account number is required before a method can be enabled.

Never put gateway secrets in templates, JavaScript, QR descriptions or the database's public payment fields. If you later integrate a gateway, put secrets in environment variables and implement the `PaymentGateway` interface in `studio/payments.py`. Its shipped implementation raises `GatewayNotConfigured`; it never reports a successful payment. Implement authenticated server-to-server initiation/verification, verify the saved order number, exact amount in paisa and currency, make callbacks idempotent, and update payment state only after successful verification. A redirect parameter or uploaded screenshot is not payment verification.

## 8. Deploy on a Docker-capable Python host

This stack needs PostgreSQL and persistent disk volumes. It is not a Cloudflare Workers/Vercel static application.

1. Copy the project to a Linux server and create `.env` from `.env.example`.
2. Generate strong independent `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` values. Set `DJANGO_ALLOWED_HOSTS` to your actual hostname plus `127.0.0.1,localhost` for health checks. Set `CSRF_TRUSTED_ORIGINS` to your actual HTTPS origin. Set `DEMO_MODE=0`, `SEED_DEMO=0`, `POSTGRES_HOST_AUTH_METHOD=scram-sha-256`, `HTTP_BIND=0.0.0.0`, and `HTTP_PORT=443`.
3. Provision a trusted TLS certificate for your domain. Put `fullchain.pem` and `privkey.pem` in `deploy/certs/`. The certificate key must be readable by the unprivileged Nginx container user (UID 101 in the configured image), while remaining inaccessible to unrelated users. Do not commit it. Arrange automated certificate renewal and Nginx reloads.
4. Start with a **new production project name**, so its database is initialized with password authentication rather than reusing the demo's trust-authenticated volume:

```bash
docker compose -p babal-production -f docker-compose.yml -f docker-compose.production.yml up --build -d
docker compose -p babal-production -f docker-compose.yml -f docker-compose.production.yml exec web python manage.py createsuperuser
docker compose -p babal-production -f docker-compose.yml -f docker-compose.production.yml exec web python manage.py check --deploy
```

The production override disables demo seeding/debug mode, requires credentials, enables secure cookies/HTTPS redirection and starts with one hour of HSTS. Increase the HSTS period only after HTTPS works consistently. Include-subdomains and preload remain explicit environment opt-ins. The supplied TLS proxy listens only on 443; add an HTTP-to-HTTPS redirect on port 80 at your hosting edge if desired. Do not point plaintext traffic at the TLS listener.

The Nginx service is the only published service. Django trusts proxy headers because Nginx overwrites them and the web port is internal. If your host adds another proxy, review its trusted forwarding chain instead of blindly passing visitor-supplied forwarding headers. On a managed platform, use its PostgreSQL service and persistent upload storage, run migrations once during release, serve public media separately, and keep private proof storage behind authorized Django views.

### Operations

- Named volumes: PostgreSQL data, public media, private media. Back up all three and test a restore before taking real orders. Database backups alone do not contain uploaded images.
- `/health/` verifies a database connection. Docker checks the database, web process and Nginx. Configure external uptime/error monitoring at your host.
- Run these daily from cron or your host scheduler; do not seed demo data in production:

```bash
docker compose exec web python manage.py clearsessions
docker compose exec web python manage.py prune_limits
```

Use the production Compose flags/project name from above for production maintenance. Decide and publish your customer-data and proof-retention policy. This project does not automatically delete uploaded files when a model record is deleted; include file cleanup in your retention/backup procedure.

## 9. Security and verification

Implemented: CSRF on forms, automatic template escaping, strict form/model choices and ranges, server prices, randomized filenames, verified/re-encoded image content, file/dimension/body limits, protected private media, session-bound idempotency, private/no-store receipt responses, honeypots, and database-backed rate limits shared by all workers.

Rate limits: checkout 10 attempts/10 minutes; tracking 20/10 minutes; reviews 5/hour; admin login 15/10 minutes per IP. A shared mobile network can share an IP, so tune limits to actual traffic. Put appropriate edge request limits in front of any public production service.

Run the application tests using SQLite:

```bash
DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test tests -v 2
```

Run against your Docker PostgreSQL service instead:

```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.test_settings -e USE_SQLITE=0 web python manage.py test tests -v 2
docker compose exec web python manage.py makemigrations --check --dry-run
```

The test role needs permission to create a temporary test database. The provided demo PostgreSQL role can do this. Do not grant this privilege to a restricted production app role just to run tests; use an isolated CI/test database.

See `docs/VALIDATION.md` for checks performed while delivering this project and environment limits. The front end needs JavaScript for canvas design, and provides a browse/DM fallback when JavaScript is disabled. Explore/review/tracking forms retain ordinary server-rendered behavior.

## 10. Placeholders to replace before launch

- Official logo, exact brand palette/fonts and approved caption tone.
- Actual tee color names/hex values, garment fit/measurements and available size range.
- All four demo prints with approved highlight artwork and real print names.
- Demo products, prices, photography and actual Instagram post links.
- NPR 1,200 base price and NPR 150 flat delivery fee.
- Merchant eSewa/Khalti/FonePay account details and QR images.
- Confirmed delivery areas, lead times, contact phone and customer-facing policies.
- Production domain, TLS certificate, secret key and PostgreSQL password.

The Instagram profile and `https://ig.me/babalwears` links are supplied by the brief. No payment details, customer reviews, fabric specifications, garment provenance or shipping promises were invented.

## References

- Django 5.2 deployment checklist: <https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/>
- Django upload security: <https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content>
- GSAP documentation: <https://gsap.com/docs/v3/>
- HTMX documentation: <https://htmx.org/docs/>
- Alpine documentation: <https://alpinejs.dev/>

Third-party notices and vendored asset versions are in `THIRD_PARTY.md`.
