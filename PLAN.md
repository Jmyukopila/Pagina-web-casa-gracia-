# Plan — Casa Gracia Direct-Booking Channel ("Canal Directo")

Goal: stop paying ~15–20% OTA commission on every booking by capturing part of
demand through your **own website + booking engine**, while keeping Booking/Airbnb
as paid acquisition channels.

---

## Phase 0 — Gather your assets (this repo)
- [x] Compile public profile → `data/casa-gracia-profile.{json,md}`
- [ ] Run the local scraper toolkit to pull your own photos/descriptions/prices
- [ ] OR (preferred) export from **Booking Extranet** + **Airbnb host dashboard**
- [ ] Collect: high-res photos, room descriptions (ES + EN), amenities,
      policies (check-in/out, cancellation, children, pets), exact GPS pin,
      logo, brand colors, official email + WhatsApp number

## Phase 1 — Single source of truth
- [ ] Finalize the 4 physical rooms (101 Queen, 201 Double, 202 King, 301 Queen)
      → map to public room types and set **direct rates** (typically price the
      direct rate **at or slightly below** the OTA rate, since you save commission)
- [ ] Decide rate plans: Flexible vs Non-refundable, breakfast included, length-of-stay
- [ ] Write copy: tagline, "why book direct" (best price guarantee, free
      late checkout, welcome drink, etc.)

## Phase 2 — Booking engine + channel manager (the core decision)
You need (a) a **booking engine** on your site that takes cards, and (b) a
**channel manager / PMS** so direct bookings and OTA bookings share one calendar
(no double-bookings).

Good fits for an 8-room independent in Colombia:
- **Cloudbeds** — PMS + booking engine + channel manager in one (popular in LATAM)
- **Little Hotelier** (by SiteMinder) — built for small properties
- **Hostaway / Lodgify / Zeevou** — strong if Airbnb/short-stay is a big share
- **Lobby PMS / Hotelisin** — Colombian/LATAM options, local support & invoicing

Payments in Colombia: **Wompi, PayU, Mercado Pago, ePayco, Bold**, or Stripe.
Make sure it handles COP + USD and issues a DIAN-valid invoice.

## Phase 3 — The website
- Domain: e.g. `casagraciacartagena.com` (check availability)
- Build options, fastest → most custom:
  1. The channel manager's built-in website builder (fastest)
  2. WordPress + a hotel booking plugin
  3. Custom site (Next.js/Astro) embedding the booking-engine widget
- Must-haves: mobile-first, ES/EN, photo gallery, room pages w/ live rates,
  map, reviews, WhatsApp click-to-chat, "Best price — book direct" banner.

## Phase 4 — Don't lose the OTA demand
- Keep Booking/Airbnb live; connect them to the **same channel manager**
- **Metasearch**: list on Google Hotels / Google Maps "Book directly" (free + paid)
- Claim **Google Business Profile** → enable "Book direct" link
- Email/WhatsApp past guests with a direct-booking offer
- Compliant with OTA rate-parity rules: don't publicly undercut; instead give
  direct-only perks (upgrade, breakfast, late checkout, member rate behind email)

## Phase 5 — Measure
- Track: direct vs OTA mix, direct conversion rate, ADR, RevPAR, commission saved
- Target: move 15–30% of bookings to direct within ~6–12 months

---

## Legal / ToS notes
- Scraping Booking/Airbnb broadly violates their ToS — only pull **your own**
  listing content, and prefer Extranet export / API / channel manager.
- Your **photos and descriptions are your IP**; you can reuse them on your own site.
- Respect **rate parity** clauses in your OTA contracts (use perks, not public
  price undercutting, to drive direct).
- Colombia specifics: register with **RNT** (Registro Nacional de Turismo),
  charge/handle tourism contributions, issue DIAN electronic invoices.
