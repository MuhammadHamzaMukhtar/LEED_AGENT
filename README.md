# Lead Finder Agent

Finds UK businesses, checks their websites, scores them as sales leads, and
(later phases) writes outreach pitches for the best ones.

## Setup (macOS)

1. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and paste in your Google Maps Demo Key:
   ```
   cp .env.example .env
   ```
   Then edit `.env` and set `GOOGLE_PLACES_API_KEY=your-key-here`.

   Note: the demo key is free with no billing, but has daily request
   limits and does not return reviews, photos, ratings, or review counts
   for most results.

## Status
Project setup complete (Phase 0). More usage instructions will be added as
each phase is built.
