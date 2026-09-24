# Lead Finder Agent

## Goal
Find UK businesses by city and category (Google Places API), check whether
each has a real working website, score them as sales leads (weak web
presence = better lead), save to CSV, and write short outreach pitches for
the best leads. We pitch web, app, and AI automation services.

## Stack
- Python 3.13, `requests`, `python-dotenv`, `pytest`
- Google Maps Demo Key (free, no billing, daily limits). No reviews/photos;
  rating and review count may be missing — handle missing fields safely.
- Key lives in `.env` as `GOOGLE_PLACES_API_KEY`, loaded via python-dotenv.

## Rules (always follow)
1. Work ONE phase at a time. After each phase: explain what was built in
   simple words, show how to test it, then STOP and wait for approval.
2. Never read, print, or log the API key or the `.env` file.
3. Use only the official Places API (New). Never scrape Google Maps, Yelp,
   or any website's search results.
4. Keep API usage low: max 10 Places requests per run by default.
5. Every function gets a docstring and clear comments. Use type hints.
   Prefer simple, readable code over clever code.
6. Handle errors clearly: invalid key, quota exceeded (RESOURCE_EXHAUSTED),
   network errors. Show a friendly message instead of a crash.
7. After a phase is approved, make a git commit with a clear message.
8. If something in the plan is unclear or risky, ask before doing it.
