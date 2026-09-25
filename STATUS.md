# Status — 2026-09-26

## Stack
- Python 3.13
- `requests`, `python-dotenv` — Places API client
- `pytest` — testing (not yet used; Phase 2/3 tests still to come)
- `streamlit`, `pandas`, `openpyxl` — dashboard UI, data handling, Excel export
- Google Maps Demo Key, stored in `.env` (git-ignored, never read/logged)
- GitHub repo: `MuhammadHamzaMukhtar/LEED_AGENT`, deployed on Streamlit
  Community Cloud

## What's done
- **Phase 0** — project setup: venv, `.gitignore`, `.env.example`,
  `.claude/settings.json` (denies reading `.env`), `CLAUDE.md`, `PLAN.md`,
  `README.md`. Committed.
- **Phase 1** — `places_client.py`: real Google Places API (New) client.
  Pagination, per-run request-limit safety cap, friendly error handling
  (bad key / quota exceeded / network errors), optional `api_key`
  override so the app isn't locked to one person's key. Committed.
- **Dashboard preview** (`dashboard_preview.py`) — ahead of the phase
  plan, but genuinely useful now: a working Streamlit app, deployed live,
  that already covers most of what Phase 7 was scoped to do:
  - New Search tab: country → all ~75 UK cities → optional town/area,
    grouped everyday-business categories, a "Target leads" number input
    (e.g. 60/100) that calculates requests needed against Google's
    60-per-category hard cap, optional per-session API key override.
  - Runs real searches against the live Places API (not mock data).
  - Best-effort email lookup: visits each lead's own website (never
    Google/Yelp) looking for a `mailto:` link or email pattern, with
    filtering to reject junk matches (CSS asset filenames, tracking
    script domains, noreply addresses).
  - Browse Results tab: filters, sort options, metric tiles, two charts,
    a scrollable results table with working website/Google Maps links,
    CSV + Excel export. Rating shown; no score number shown anywhere.
  - Pitches tab: auto-drafted outreach text for the strongest leads,
    angled by website status, with the PECR/Companies House reminder.
  - No data shown until a real search is run; no fields pre-selected
    except country.

## What's not done yet (per PLAN.md's phase order)
- Phase 2 — `website_checker.py`: real live HTTP check per site (the
  dashboard currently only checks "has a website" vs not, not whether
  it's actually live/broken/parked)
- Phase 3 — a proper, tested lead-ranking module (currently informal
  logic inline in the dashboard; not yet extracted or unit-tested, and
  the exact ranking approach is still open to revisit)
- Phase 4 — `lead_finder.py` CLI
- Phase 5 — Claude Code subagents (`lead-researcher`, `pitch-writer`) and
  the `/find-leads` skill
- Phase 6 — final docs pass
- Phase 7 — folding the dashboard preview's logic into the real,
  tested `dashboard.py`, backed by the modules above instead of inline
  logic

## Known limitations to keep in mind
- Website status in the dashboard is simplified (no live check yet)
- Email lookup is best-effort; most small-business sites won't have one
- Deployed app uses either the developer's `.env` key or whatever key a
  visitor types in — no per-user quota tracking beyond the on-page count
