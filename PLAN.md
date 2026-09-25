# Lead Finder Agent: Build Plan

## Goal
Build an internal tool + Claude Code agent that:
1. Finds UK businesses by city and category using the Google Places API (New)
2. Checks whether each business has a real, working website
3. Scores each business as a sales lead (weak web presence = better lead)
4. Saves results to CSV
5. Writes short personalised outreach pitches for the best leads
We will pitch these businesses our web, app, and AI automation services.

## About the developer
- New to building AI agents, learning step by step
- macOS, VS Code, Python 3.13 (use python3 outside the venv)
- Explain every phase in simple language

## Constraints
- API key: Google Maps Demo Key (free, no billing, daily request limits)
- The demo key does NOT return reviews or photos. Rating and review
  count may also be missing. The code must handle missing fields safely.
- Key is stored in `.env` as GOOGLE_PLACES_API_KEY and loaded with python-dotenv

## Rules (always follow)
1. Work ONE phase at a time. After each phase: explain what you built in
   simple words, show how to test it, then STOP and wait for me to say "continue".
2. Never read, print, or log the API key or the `.env` file.
3. Use only the official Places API (New). Never scrape Google Maps, Yelp,
   or any website's search results.
4. Keep API usage low: max 10 Places requests per run by default.
5. Every function gets a docstring and clear comments. Use type hints.
   Prefer simple, readable code over clever code.
6. Handle errors clearly: invalid key, quota exceeded (RESOURCE_EXHAUSTED),
   network errors. Show a friendly message instead of a crash.
7. After I approve a phase, make a git commit with a clear message.
8. If something in this plan is unclear or risky, ask me before doing it.

## Project structure (target)
```
lead_agent/
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── lead-researcher.md
│   │   └── pitch-writer.md
│   └── skills/
│       └── find-leads/
│           └── SKILL.md
├── leads/                 # output CSVs (git-ignored)
├── tests/
│   ├── test_website_checker.py
│   └── test_scoring.py
├── places_client.py       # talks to Google Places API
├── website_checker.py     # checks if a website is real and working
├── scoring.py             # gives each lead a score
├── lead_finder.py         # main command-line script
├── .env                   # my key (git-ignored, never read it)
├── .env.example
├── .gitignore
├── CLAUDE.md
├── PLAN.md
├── README.md
└── requirements.txt
```

---

## Phase 0: Project setup
Skip anything that already exists.
- Create venv (`python3 -m venv venv`)
- requirements.txt: requests, python-dotenv, pytest. Install into venv.
- `git init`
- .gitignore: venv/, .env, leads/, __pycache__/, .pytest_cache/
- .env.example with `GOOGLE_PLACES_API_KEY=`
- .claude/settings.json: deny reading .env
- CLAUDE.md: short summary of goal, stack, and the Rules above
- README.md: macOS setup steps
Done when: I can run `source venv/bin/activate` and `pip list` shows the packages.

## Phase 1: Places API client (`places_client.py`)
- Function `search_places(query: str, max_pages: int, request_limit: int) -> list[dict]`
- POST to `https://places.googleapis.com/v1/places:searchText`
- Headers: X-Goog-Api-Key (from .env), X-Goog-FieldMask
- Field mask: places.id, places.displayName, places.formattedAddress,
  places.nationalPhoneNumber, places.websiteUri, places.businessStatus,
  places.primaryType, places.googleMapsUri, places.rating,
  places.userRatingCount, nextPageToken
- Follow nextPageToken for pagination (pageSize 20, short pause between pages)
- Count every request and stop at request_limit
- Return a clean list of dicts with simple keys (name, address, phone,
  website, status, category, maps_url, rating, reviews, place_id);
  use None for missing fields
- Add a tiny test mode: `python places_client.py` searches
  "hair salon in Manchester, UK" with pageSize 5 and prints the results
Done when: the test mode prints 5 real businesses.

## Phase 2: Website checker (`website_checker.py`)
- Function `check_website(url: str | None) -> tuple[str, str]` returning (status, detail)
- Statuses:
  - NO_WEBSITE: no URL
  - SOCIAL_ONLY: facebook, instagram, linktr.ee, wa.me, tiktok, x/twitter,
    linkedin, yell.com, business.site (also if the site redirects to one)
  - BROKEN: DNS error, timeout, SSL error, HTTP 4xx/5xx
  - UNKNOWN: HTTP 401/403/429 (likely bot protection, not broken)
  - PARKED: page contains "domain is for sale", "buy this domain", etc.
  - NO_HTTPS: works but final URL is not https
  - OK: working https website
- 10 second timeout, follow redirects, realistic User-Agent,
  only read the first 20,000 characters of the page
- Unit tests in tests/test_website_checker.py using mocked responses
  (no real network calls in tests), one test per status
Done when: `pytest` passes.

## Phase 3: Scoring (`scoring.py`)
- Function `score_lead(lead: dict) -> int`
- Website status points: NO_WEBSITE 50, BROKEN 45, PARKED 45,
  SOCIAL_ONLY 40, NO_HTTPS 25, UNKNOWN 10, OK 0
- +10 if phone exists
- If reviews exist: + min(reviews // 10, 30); +10 if rating >= 4.0
- If rating/reviews are missing, just skip those points (demo key)
- Unit tests in tests/test_scoring.py
Done when: `pytest` passes.

## Phase 4: Main script (`lead_finder.py`)
- Command line:
  `python lead_finder.py --city "Manchester, UK" --categories "hair salon,plumber" --limit 10`
- For each category: search_places("<category> in <city>")
- Remove duplicates by place_id
- Skip businesses where status is not OPERATIONAL
- Check each website, score each lead
- Sort by score (highest first)
- Save to `leads/<city-slug>-<YYYY-MM-DD>.csv`
- Print a summary: total leads, count per website status, top 5 leads
Done when: a real run with 1 city and 2 categories creates a CSV.

## Phase 5: Claude Code agent layer
Create these files (Claude Code subagents and a skill):

1. `.claude/agents/lead-researcher.md`
   - Frontmatter: name, description, tools (Bash, Read, Write, Glob, WebFetch), model: inherit
   - Job: run lead_finder.py with the given city/categories, then verify
     rows with status UNKNOWN and the top 5 BROKEN/PARKED rows using WebFetch,
     save a `-verified.csv` copy with a `verified_note` column,
     return a short summary (counts per status, top 10 table, corrections)
   - Must never read .env, never modify code, never contact businesses

2. `.claude/agents/pitch-writer.md`
   - Frontmatter: name, description, tools (Read, Write), model: inherit
   - Job: read the verified CSV, take leads with score >= 50 (max 20),
     write a pitch per lead (max 80 words, British English, friendly,
     one true detail from the CSV, one call to action for a 15-minute call,
     end with an opt-out line)
   - Pitch angle by status:
     NO_WEBSITE/BROKEN/PARKED: simple website + WhatsApp booking bot
     SOCIAL_ONLY: automate Instagram/WhatsApp enquiries, then a website
     NO_HTTPS: security fix + enquiry chatbot
     OK: AI automation only (chatbot, lead capture, reminders)
   - Save to `leads/<name>-pitches.md`
   - Never invent facts about a business
   - Top of file note: "Check Companies House before emailing. Sole traders
     and partnerships need prior consent for marketing email (PECR)."

3. `.claude/skills/find-leads/SKILL.md`
   - Frontmatter: name: find-leads, description, argument-hint: <city> | <categories>
   - Parses $ARGUMENTS as "city | categories", asks if missing
   - Uses lead-researcher, then pitch-writer
   - Replies with file paths, counts per status, top 5 leads, reminders

4. Update .claude/settings.json to allow `Bash(python lead_finder.py:*)`
   without asking, while still denying .env
Done when: after restarting Claude Code, `/agents` shows both agents.

## Phase 6: Final test and docs
- Run `/find-leads Manchester, UK | hair salon,plumber` end to end
- Update README.md: how to run the script, how to use /find-leads,
  what each website status means, demo key limits
- Final commit

## Phase 7: Dashboard (`dashboard.py`)
- Add `streamlit`, `pandas`, and `openpyxl` to requirements.txt and install them
- Bundle a free, offline country/state/city dataset as a local JSON file
  (e.g. the open-source "countries+states+cities" dataset, MIT licensed) in
  `data/locations.json`. No external API, no key, no cost, no quota risk.
- Bundle a preset list of everyday UK local-business categories, grouped
  by sector, as a local Python list/JSON in the same `data/` folder as
  the location dataset:
  - Health & wellbeing: GP surgery, dentist, optician, pharmacy,
    physiotherapist, chiropractor, vet, gym, yoga studio, massage
    therapist, osteopath, nutritionist
  - Food & drink: cafe, restaurant, takeaway, pub, bakery, butcher,
    caterer, coffee shop
  - Home trades: plumber, electrician, builder, roofer, painter &
    decorator, gardener/landscaper, locksmith, cleaner, handyman, pest
    control, removals
  - Personal care & beauty: hair salon, barber, nail salon, beauty
    salon, tattoo studio, tanning salon
  - Professional services: accountant, solicitor, estate agent,
    insurance broker, financial advisor, recruitment agency,
    photographer
  - Automotive: mechanic, MOT centre, car wash, car dealership, tyre
    shop, driving instructor
  - Retail & other: florist, pet shop, charity shop, dry cleaner,
    bookshop, hardware store
- Create `dashboard.py` using Streamlit with three tabs: "New Search",
  "Browse Results", and "Pitches".

  ### Tab 1: New Search
  - Country dropdown (from the bundled dataset)
  - City dropdown, filtered to the chosen country (from the same dataset)
  - Optional free-text town/area box, for places finer-grained than the
    bundled city list (e.g. "Hebden Bridge" inside "West Yorkshire")
  - Alternative toggle: "Search whole city" vs "Search a specific
    town/area within it" — whole-city just uses the city name as-is
  - Categories: multi-select checklist from the bundled preset list, plus
    an "add custom category" text box for anything not listed
  - Target leads as a number input (e.g. 60 or 100), not a slider or
    preset tier: converts to requests needed (leads / 20, capped at
    categories_count x 3, since 60 results / 3 requests per category is
    Google's own hard cap). Shows a warning, not an error, if the target
    exceeds what's possible for the categories picked -- the search still
    runs and returns the max available
  - Optional API key field: overrides the .env key for this run only,
    never stored or logged -- lets someone other than the developer use
    the app with their own key/quota
  - "Run search" button: calls the existing search_places /
    check_website / score_lead functions directly (no API key ever
    shown or logged), shows a progress spinner, then saves a CSV to
    leads/ exactly like the CLI does
  - Clear warning near the button showing how many requests this run
    will use, so nobody accidentally blows the daily demo quota
  - Email lookup: Google Places has no email field, so for each lead
    that has a website, visit that business's own site (never Google
    Maps/Yelp/any search engine -- this doesn't conflict with rule 3)
    and look for a mailto: link or an email pattern on the page.
    Best-effort only, silently skipped on any error, capped at ~50 sites
    per run to keep searches fast

  ### Tab 2: Browse Results
  - Sidebar: pick a CSV from the `leads/` folder (newest first)
  - Sidebar filters: website status (multi-select), category (multi-select),
    minimum score (slider)
  - Top row metric cards: total leads, NO_WEBSITE count, SOCIAL_ONLY count,
    BROKEN + PARKED count, average score
  - Bar chart: number of leads per website status
  - Bar chart: number of leads per category
  - Table of filtered leads sorted by score (highest first), showing
    name, address, category, website_status, phone, rating, reviews,
    score, website, email, maps_url (rating/reviews may be blank -- the
    demo key often doesn't return them; email may be blank -- best-effort
    lookup, not every site publishes one)
  - Make website and maps_url clickable links
  - Download buttons for the filtered table: CSV and real .xlsx (via
    openpyxl)
  - If no CSV exists in leads/, show a friendly message pointing to the
    "New Search" tab

  ### Tab 3: Pitches
  - Pick a verified/scored CSV, same picker as Tab 2
  - Shows the leads with score >= 50 (max 20), same rule as the
    pitch-writer agent from Phase 5
  - "Generate pitches" button: runs the same pitch-writing logic used by
    the pitch-writer agent (as a shared Python function, not a duplicate
    copy) and saves a `-pitches.md` file to leads/, same as today
  - Read-only view of each generated pitch (business name, status,
    pitch text) with a "copy to clipboard" button per pitch
  - Same legal reminder shown at the top: check Companies House, PECR
    consent rules for sole traders/partnerships
  - No email sending, no contacting businesses from the app — pitches are
    for you to copy and send yourself

- Do not show businesses on a map (Google Places terms)
- The only Google API calls happen from the "New Search" tab's button,
  through the same request-limit-checked functions as the CLI; nothing
  else in the dashboard ever calls the API
- Add run instructions to README.md: `streamlit run dashboard.py`
Done when: `streamlit run dashboard.py` opens in my browser, I can pick a
country and city from dropdowns, select categories from a checklist, run
a small search, see it appear in Browse Results, export it as CSV and
.xlsx, and generate + read pitches for the top leads in the Pitches tab.
