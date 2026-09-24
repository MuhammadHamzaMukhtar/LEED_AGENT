"""PREVIEW ONLY -- not the real Phase 7 deliverable.

This is an early mockup of the planned dashboard.py, built to let you click
through the intended layout before Phases 2-6 (website checker, scoring,
CLI, agents) are all built. "Run search" now calls the REAL places_client.py
(Phase 1) and shows REAL Google Places results -- your API key is used and
counted against your daily quota when you click it. Website status/score are
a simplified stand-in for the real logic Phase 2/3 will add (no live
HTTP check of each site yet, just "has a website or not").

Run with: streamlit run dashboard_preview.py
"""

import datetime
import io
import math
import os
import re

import pandas as pd
import streamlit as st

from places_client import PlacesApiError, search_places

st.set_page_config(page_title="Lead Finder (Preview)", layout="wide")

# --- Visual polish: fonts, header banner, cards, badges ---------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }

    .lf-hero {
        background: linear-gradient(135deg, #2a78d6 0%, #1c5cab 100%);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 20px;
        color: #ffffff;
    }
    .lf-hero h1 {
        margin: 0 0 4px 0;
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
    }
    .lf-hero p {
        margin: 0;
        font-size: 14px;
        color: rgba(255,255,255,0.88);
    }
    .lf-badge {
        display: inline-block;
        margin-top: 10px;
        padding: 4px 12px;
        background: rgba(255,255,255,0.16);
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e1e0d9;
        border-radius: 12px;
        padding: 14px 16px 10px;
        box-shadow: 0 1px 2px rgba(11,11,11,0.04);
    }
    div[data-testid="stMetricLabel"] { font-weight: 600; color: #52514e; }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
    }
    .status-pill::before {
        content: "";
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
        flex-shrink: 0;
    }
    .status-ok { background: rgba(12,163,12,0.12); color: #0a7a0a; }
    .status-warn { background: rgba(250,178,25,0.20); color: #97650a; }
    .status-bad { background: rgba(208,59,59,0.12); color: #b8302f; }
    .status-unknown { background: rgba(137,135,129,0.16); color: #6b6a65; }

    .maps-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 999px;
        background: rgba(42,120,214,0.10);
        color: #1c5cab;
        font-size: 12px;
        font-weight: 700;
        text-decoration: none;
        white-space: nowrap;
    }
    .maps-pill:hover { background: rgba(42,120,214,0.18); }

    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #e1e0d9;
    }

    div[data-testid="stSegmentedControl"] label {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] > div,
    div[data-testid="stMultiSelect"] > div {
        border-radius: 8px !important;
    }

    h1, h2, h3 { letter-spacing: -0.01em; }

    button[kind="primary"] {
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    section[data-testid="stSidebar"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# All official UK cities (England, Scotland, Wales, Northern Ireland),
# alphabetical. This is the full list, not a sample -- you can search any
# of these directly, or use "Specific town/area" to narrow within one.
UK_CITIES = sorted([
    # England
    "Bath", "Birmingham", "Bradford", "Brighton & Hove", "Bristol",
    "Cambridge", "Canterbury", "Carlisle", "Chelmsford", "Chester",
    "Chichester", "Colchester", "Coventry", "Derby", "Doncaster", "Durham",
    "Ely", "Exeter", "Gloucester", "Hereford", "Kingston upon Hull",
    "Lancaster", "Leeds", "Leicester", "Lichfield", "Lincoln", "Liverpool",
    "London", "Manchester", "Milton Keynes", "Newcastle upon Tyne",
    "Norwich", "Nottingham", "Oxford", "Peterborough", "Plymouth",
    "Portsmouth", "Preston", "Ripon", "Salford", "Salisbury", "Sheffield",
    "Southampton", "Southend-on-Sea", "St Albans", "Stoke-on-Trent",
    "Sunderland", "Truro", "Wakefield", "Wells", "Westminster",
    "Winchester", "Wolverhampton", "Worcester", "York",
    # Scotland
    "Aberdeen", "Dundee", "Dunfermline", "Edinburgh", "Glasgow",
    "Inverness", "Perth", "Stirling",
    # Wales
    "Bangor", "Cardiff", "Newport", "St Asaph", "St Davids", "Swansea",
    "Wrexham",
    # Northern Ireland
    "Armagh", "Belfast", "Derry", "Lisburn", "Newry",
])

SAMPLE_LOCATIONS = {
    "United Kingdom": UK_CITIES,
    "Ireland": ["Dublin", "Cork", "Galway", "Limerick", "Waterford"],
}

# Grouped by everyday sector so the picker stays browsable. This mirrors
# what a normal UK high street / local search covers -- health, food,
# home trades, personal care, retail, professional and auto services.
CATEGORY_GROUPS = {
    "Health & wellbeing": [
        "Doctor / GP surgery", "Dentist", "Optician", "Pharmacy",
        "Physiotherapist", "Chiropractor", "Vet", "Gym", "Yoga studio",
        "Massage therapist", "Osteopath", "Nutritionist",
    ],
    "Food & drink": [
        "Cafe", "Restaurant", "Takeaway", "Pub", "Bakery", "Butcher",
        "Caterer", "Coffee shop",
    ],
    "Home trades": [
        "Plumber", "Electrician", "Builder", "Roofer", "Painter & decorator",
        "Gardener / landscaper", "Locksmith", "Cleaner", "Handyman",
        "Pest control", "Removals company",
    ],
    "Personal care & beauty": [
        "Hair salon", "Barber", "Nail salon", "Beauty salon", "Tattoo studio",
        "Tanning salon",
    ],
    "Professional services": [
        "Accountant", "Solicitor", "Estate agent", "Insurance broker",
        "Financial advisor", "Recruitment agency", "Photographer",
    ],
    "Automotive": [
        "Mechanic", "MOT centre", "Car wash", "Car dealership", "Tyre shop",
        "Driving instructor",
    ],
    "Retail & other": [
        "Florist", "Pet shop", "Charity shop", "Dry cleaner", "Bookshop",
        "Hardware store",
    ],
}
SAMPLE_CATEGORIES = [c for group in CATEGORY_GROUPS.values() for c in group]

STATUS_BADGE = {
    "NO_WEBSITE": ("status-bad", "No website"),
    "BROKEN": ("status-bad", "Broken"),
    "PARKED": ("status-bad", "Parked"),
    "SOCIAL_ONLY": ("status-warn", "Social only"),
    "NO_HTTPS": ("status-warn", "No HTTPS"),
    "UNKNOWN": ("status-unknown", "Unknown"),
    "OK": ("status-ok", "Live site"),
}


def status_pill_html(status: str) -> str:
    """Render a website status as a small colored HTML pill."""
    css_class, label = STATUS_BADGE.get(status, ("status-unknown", status))
    return f'<span class="status-pill {css_class}">{label}</span>'


def website_link_html(website: str) -> str:
    """Turn a website value into a real clickable link.

    Google already returns full URLs (e.g. "http://example.com"), so we
    must NOT prepend another "https://" on top of that -- doing so used to
    produce broken links like "https://http://example.com" that opened the
    wrong page."""
    if not website:
        return "—"
    href = website if website.startswith(("http://", "https://")) else f"https://{website}"
    display_text = re.sub(r"^https?://(www\.)?", "", website).rstrip("/")
    return f'<a href="{href}" target="_blank" rel="noopener">{display_text}</a>'


def maps_link_html(maps_url: str) -> str:
    """Render the Google Maps link as a small button-style pill."""
    if not maps_url:
        return "—"
    return (
        f'<a href="{maps_url}" target="_blank" rel="noopener" '
        f'class="maps-pill">View on Maps</a>'
    )


STATUS_POINTS = {
    "NO_WEBSITE": 50, "BROKEN": 45, "PARKED": 45, "SOCIAL_ONLY": 40,
    "NO_HTTPS": 25, "UNKNOWN": 10, "OK": 0,
}


def _score_lead(status: str, phone: str, rating: float | None, reviews: int | None) -> int:
    """Same formula as the planned scoring.py (Phase 3): status points +
    phone/rating/review bonuses. Kept here so the mockup's fake data is at
    least internally consistent with the real design."""
    score = STATUS_POINTS[status]
    if phone:
        score += 10
    if reviews:
        score += min(reviews // 10, 30)
    if rating and rating >= 4.0:
        score += 10
    return score


SOCIAL_DOMAINS = [
    "facebook.com", "instagram.com", "linktr.ee", "wa.me", "tiktok.com",
    "twitter.com", "x.com", "linkedin.com", "yell.com", "business.site",
]


def _simple_website_status(website: str | None) -> str:
    """Rough stand-in for the real website_checker.py (Phase 2), which will
    actually visit each site and check if it's live, broken, or parked.
    For now this only tells NO_WEBSITE vs SOCIAL_ONLY vs OK, since we
    haven't built the live HTTP check yet."""
    if not website:
        return "NO_WEBSITE"
    if any(domain in website.lower() for domain in SOCIAL_DOMAINS):
        return "SOCIAL_ONLY"
    return "OK"


def run_real_search(
    location_label: str, categories: list[str], request_budget: int,
    api_key: str | None = None,
) -> tuple[pd.DataFrame, int, list[str]]:
    """Call the real Places API (via places_client.search_places) for each
    category, spending at most request_budget requests in total across all
    of them. Returns (leads_df, requests_actually_used, error_messages).

    api_key, if given, overrides the .env key -- lets each user of the app
    supply their own key instead of the developer's."""
    remaining = request_budget
    rows = []
    seen_place_ids = set()
    errors = []
    requests_used = 0

    for category in categories:
        if remaining <= 0:
            break
        query = f"{category} in {location_label}"
        try:
            places = search_places(
                query, max_pages=3, request_limit=remaining, api_key=api_key
            )
        except PlacesApiError as error:
            errors.append(f"{category}: {error}")
            continue

        used_this_call = min(remaining, max(1, math.ceil(len(places) / 20)))
        requests_used += used_this_call
        remaining -= used_this_call

        for place in places:
            if place.get("status") != "OPERATIONAL":
                continue
            place_id = place.get("place_id")
            if place_id and place_id in seen_place_ids:
                continue
            if place_id:
                seen_place_ids.add(place_id)

            website = place.get("website")
            phone = place.get("phone")
            rating = place.get("rating")
            reviews = place.get("reviews")
            status = _simple_website_status(website)

            rows.append({
                "name": place.get("name") or "(unnamed)",
                "address": place.get("address") or "—",
                "category": category,
                "website_status": status,
                "phone": phone or "",
                "rating": rating,
                "reviews": reviews,
                "score": _score_lead(status, phone or "", rating, reviews),
                "website": website or "",
                "maps_url": place.get("maps_url") or "",
            })

    columns = [
        "name", "address", "category", "website_status", "phone",
        "rating", "reviews", "score", "website", "maps_url",
    ]
    df = pd.DataFrame(rows, columns=columns)
    return df, requests_used, errors


def slugify(text: str) -> str:
    """Turn a location label into a filename-safe slug, same style the
    real lead_finder.py will use for leads/<city-slug>-<date>.csv."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


EMPTY_LEADS = pd.DataFrame(columns=[
    "name", "address", "category", "website_status", "phone",
    "rating", "reviews", "score", "website", "maps_url",
])

if "search_results" not in st.session_state:
    st.session_state["search_results"] = EMPTY_LEADS
    st.session_state["search_label"] = ""
    st.session_state["search_filename"] = ""
    st.session_state["last_search_requests"] = 0
    st.session_state["requests_used_today"] = 0
    st.session_state["has_searched"] = False

DAILY_REQUEST_ALLOWANCE = 100  # typical Places API (New) free daily quota, adjust to your actual cap

# --- Header ------------------------------------------------------------
requests_today = st.session_state["requests_used_today"]
quota_pct = min(requests_today / DAILY_REQUEST_ALLOWANCE, 1.0)
quota_color = "#0ca30c" if quota_pct < 0.7 else ("#fab219" if quota_pct < 0.9 else "#d03b3b")
st.markdown(
    f"""
    <div class="lf-hero">
        <h1>Lead Finder</h1>
        <p>Find local businesses with weak web presence, score them as sales leads, and draft outreach in one place.</p>
        <span class="lf-badge">Preview build &middot; New Search uses your real API key &middot; website status is simplified until Phase 2</span>
        <span class="lf-badge" style="background: rgba(255,255,255,0.22);">
            API usage today: <b>{requests_today} / {DAILY_REQUEST_ALLOWANCE}</b>
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{quota_color}; margin-left:6px; vertical-align:middle;"></span>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_search, tab_browse, tab_pitches = st.tabs(
    ["New Search", "Browse Results", "Pitches"]
)

# --- Tab 1: New Search -------------------------------------------------
with tab_search:
    with st.expander("API key", expanded=not bool(os.environ.get("GOOGLE_PLACES_API_KEY"))):
        st.caption(
            "Uses the key from this project's .env file by default. Enter "
            "your own Google Places API key here to use it instead -- useful "
            "if this app is shared and you don't want to use the developer's "
            "key or quota. Never stored, shown again, or written to any file."
        )
        typed_api_key = st.text_input(
            "Google Places API key (optional)", type="password",
            placeholder="Leave blank to use the project's .env key",
        )

    with st.container(border=True):
        st.subheader("Find businesses in a location")
        col1, col2, col3 = st.columns(3)

        with col1:
            country = st.selectbox(
                "Country", list(SAMPLE_LOCATIONS.keys()), index=0,
            )  # United Kingdom is first in SAMPLE_LOCATIONS, so this is the only pre-picked field
        with col2:
            city = st.selectbox(
                "City", SAMPLE_LOCATIONS[country], index=None,
                placeholder="Select a city",
            )
        with col3:
            st.markdown("**Scope**")
            scope = st.segmented_control(
                "Scope",
                options=["Whole city", "Specific town/area"],
                label_visibility="collapsed",
            )

        town = ""
        if scope == "Specific town/area":
            town = st.text_input("Town / area (optional)", placeholder="e.g. Chorlton")

        st.markdown("**Categories**")
        chosen_categories = st.multiselect(
            "Pick one or more categories", SAMPLE_CATEGORIES,
            label_visibility="collapsed",
        )
        custom_category = st.text_input("Add a custom category (optional)")

        categories_count = max(
            len(chosen_categories) + (1 if custom_category else 0), 1
        )
        full_requests = categories_count * 3  # Google's own per-category cap

        st.markdown("**Search depth**")
        depth_choice = st.segmented_control(
            "Search depth",
            options=["Quick", "Standard", "Thorough", "Full"],
            label_visibility="collapsed",
        )
        REQUEST_BUDGET = {"Quick": 3, "Standard": 5, "Thorough": 10, "Full": full_requests}
        request_limit = REQUEST_BUDGET.get(depth_choice or "Standard", 5)
        st.caption(
            f"Quick ≈ 3 requests · Standard ≈ 5 requests · "
            f"Thorough ≈ 10 requests · Full = every result Google has "
            f"for your categories (currently {full_requests} requests, "
            f"{categories_count} categor{'y' if categories_count == 1 else 'ies'} "
            f"× 3, Google's own per-category cap)"
        )

        if not city:
            st.info("Select a city to continue.")
        elif not chosen_categories and not custom_category:
            st.info("Pick at least one category to continue.")
        elif not depth_choice:
            st.info("Choose a search depth to continue.")
        else:
            location_label = f"{town + ', ' if town else ''}{city}, {country}"
            if depth_choice == "Full":
                st.info(
                    f"**Full** will fetch every business Google returns for "
                    f"**{categories_count} categor{'y' if categories_count == 1 else 'ies'}** "
                    f"in **{location_label}** — up to **{request_limit} requests**, "
                    f"nothing held back."
                )
            else:
                st.info(
                    f"This search will use up to **{request_limit} requests** across "
                    f"**{categories_count} categor{'y' if categories_count == 1 else 'ies'}** "
                    f"in **{location_label}**."
                )

            if st.button("Run search", type="primary"):
                all_categories = chosen_categories + ([custom_category] if custom_category else [])
                with st.spinner("Searching Google Places live..."):
                    results, actual_requests, errors = run_real_search(
                        location_label, all_categories, request_limit,
                        api_key=typed_api_key or None,
                    )

                for message in errors:
                    st.error(message)

                today = datetime.date.today().isoformat()
                st.session_state["search_results"] = results
                st.session_state["search_label"] = location_label
                st.session_state["search_filename"] = f"{slugify(location_label)}-{today}.csv"
                st.session_state["last_search_requests"] = actual_requests
                st.session_state["requests_used_today"] += actual_requests
                st.session_state["has_searched"] = True

                if len(results) > 0:
                    st.success(
                        f"Found {len(results)} real businesses in "
                        f"{location_label}. Switch to the Browse Results tab to see them."
                    )
                elif not errors:
                    st.warning(
                        f"No operational businesses found for these categories in "
                        f"{location_label}. Try a bigger area or different categories."
                    )
                st.caption(
                    f"Used **{actual_requests} API request"
                    f"{'s' if actual_requests != 1 else ''}** for this search. "
                    f"Total used today: **{st.session_state['requests_used_today']} / "
                    f"{DAILY_REQUEST_ALLOWANCE}** (adjust this cap to your actual demo-key quota). "
                    f"Website status here is simplified (no live site check yet -- that's Phase 2)."
                )

# --- Tab 2: Browse Results ----------------------------------------------
with tab_browse:
    active_leads = st.session_state["search_results"]

    if not st.session_state["has_searched"] or len(active_leads) == 0:
        st.info(
            "No results yet. Go to the New Search tab, pick a location and "
            "categories, and run a search to see leads here."
            if not st.session_state["has_searched"] else
            "The last search found no operational businesses. Try a "
            "different location or categories in the New Search tab."
        )
    else:
        st.subheader(
            f"{st.session_state['search_label']} — "
            f"{st.session_state['search_filename']}"
        )

        with st.container(border=True):
            fcol1, fcol2, fcol3 = st.columns(3)
            with fcol1:
                status_filter = st.multiselect(
                    "Website status", sorted(active_leads["website_status"].unique()),
                    default=sorted(active_leads["website_status"].unique()),
                )
            with fcol2:
                category_filter = st.multiselect(
                    "Category", sorted(active_leads["category"].unique()),
                    default=sorted(active_leads["category"].unique()),
                )
            with fcol3:
                st.markdown("**Lead heat**")
                heat_choice = st.segmented_control(
                    "Minimum score",
                    options=["All leads", "Warm 30+", "Hot 50+", "Very hot 70+"],
                    default="All leads",
                    label_visibility="collapsed",
                )
                HEAT_THRESHOLD = {
                    "All leads": 0, "Warm 30+": 30, "Hot 50+": 50, "Very hot 70+": 70,
                }
                min_score = HEAT_THRESHOLD.get(heat_choice or "All leads", 0)

            st.markdown("**Sort by**")
            sort_choice = st.segmented_control(
                "Sort by",
                options=[
                    "Best lead first", "Rating: High to low", "Rating: Low to high",
                    "Reviews: High to low", "Reviews: Low to high", "Name: A to Z",
                ],
                default="Best lead first",
                label_visibility="collapsed",
            )

        SORT_RULES = {
            "Best lead first": ("score", False),
            "Rating: High to low": ("rating", False),
            "Rating: Low to high": ("rating", True),
            "Reviews: High to low": ("reviews", False),
            "Reviews: Low to high": ("reviews", True),
            "Name: A to Z": ("name", True),
        }
        sort_column, sort_ascending = SORT_RULES.get(sort_choice or "Best lead first", ("score", False))

        filtered = active_leads[
            active_leads["website_status"].isin(status_filter)
            & active_leads["category"].isin(category_filter)
            & (active_leads["score"] >= min_score)
        ].sort_values(sort_column, ascending=sort_ascending, na_position="last")

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Total leads", len(filtered))
        m2.metric("No website", (filtered["website_status"] == "NO_WEBSITE").sum())
        m3.metric("Social only", (filtered["website_status"] == "SOCIAL_ONLY").sum())
        m4.metric("Broken/Parked", filtered["website_status"].isin(["BROKEN", "PARKED"]).sum())
        m5.metric("Average rating", round(filtered["rating"].mean(), 1) if filtered["rating"].notna().any() else "—")
        m6.metric("API requests used", st.session_state["last_search_requests"])

        st.write("")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            with st.container(border=True):
                st.caption("Leads per website status")
                st.bar_chart(filtered["website_status"].value_counts(), color="#2a78d6")
        with chart_col2:
            with st.container(border=True):
                st.caption("Leads per category")
                st.bar_chart(filtered["category"].value_counts(), color="#1baf7a")

        st.write("")
        st.markdown("**Leads**")

        display_df = filtered.copy()
        display_df["status"] = display_df["website_status"].apply(status_pill_html)
        display_df = display_df[[
            "name", "address", "category", "status", "phone",
            "rating", "reviews", "website", "maps_url",
        ]]
        display_df = display_df.rename(columns={
            "name": "Name", "address": "Address (exact)", "category": "Category",
            "status": "Status", "phone": "Phone", "rating": "Rating",
            "reviews": "Reviews", "website": "Website", "maps_url": "Google Maps",
        })

        table_html = display_df.to_html(
            escape=False, index=False,
            formatters={
                "Rating": lambda r: f"{r:.1f} / 5" if pd.notna(r) else "—",
                "Reviews": lambda r: f"{int(r)}" if pd.notna(r) else "—",
                "Phone": lambda p: p if p else "—",
                "Website": website_link_html,
                "Google Maps": maps_link_html,
            },
        )
        table_html = table_html.replace(
            "<table", '<table style="width:100%; border-collapse:collapse; font-size:13px;"'
        ).replace(
            "<th>", '<th style="text-align:left; padding:8px 10px; border-bottom:2px solid #e1e0d9; '
                    'text-transform:uppercase; font-size:11px; color:#898781; letter-spacing:0.03em; '
                    'position:sticky; top:0; background:#fcfcfb; z-index:1;">'
        ).replace(
            "<td>", '<td style="padding:9px 10px; border-bottom:1px solid #e1e0d9; vertical-align:middle; '
                    'white-space:nowrap;">'
        )
        st.markdown(
            f'<div style="max-height:480px; overflow-y:auto; overflow-x:auto; '
            f'border:1px solid #e1e0d9; border-radius:10px;">{table_html}</div>',
            unsafe_allow_html=True,
        )

        st.write("")
        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        excel_buffer = io.BytesIO()
        filtered.to_excel(excel_buffer, index=False, engine="openpyxl")

        dl1, dl2, _ = st.columns([1, 1, 3])
        dl1.download_button("Download CSV", csv_bytes, "leads.csv", "text/csv")
        dl2.download_button(
            "Download Excel (.xlsx)", excel_buffer.getvalue(), "leads.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

PITCH_ANGLE = {
    "NO_WEBSITE": "a simple website with WhatsApp booking built in",
    "BROKEN": "a simple website with WhatsApp booking built in",
    "PARKED": "a simple website with WhatsApp booking built in",
    "SOCIAL_ONLY": "automating your Instagram/WhatsApp enquiries, then a proper website",
    "NO_HTTPS": "a quick security fix plus an enquiry chatbot",
    "OK": "AI automation — a chatbot, lead capture, and appointment reminders",
    "UNKNOWN": "a simple website with WhatsApp booking built in",
}


def build_fallback_pitch(lead: pd.Series) -> str:
    angle = PITCH_ANGLE.get(lead["website_status"], PITCH_ANGLE["NO_WEBSITE"])
    detail = (
        f"with a {lead['rating']:.1f}-star rating" if pd.notna(lead["rating"])
        else f"in {lead['address'].split(',')[-2].strip() if ',' in lead['address'] else 'the area'}"
    )
    return (
        f"Hi, I came across {lead['name']} {detail} and thought I'd reach out. "
        f"We help local {lead['category'].lower()} businesses with {angle}, so more "
        f"customers can find and book you directly. Would you be open to a quick "
        f"15-minute call to see if it's a fit? Reply 'no thanks' if not interested "
        f"and I won't follow up."
    )


# --- Tab 3: Pitches -------------------------------------------------------
with tab_pitches:
    active_leads = st.session_state["search_results"]

    if not st.session_state["has_searched"] or len(active_leads) == 0:
        st.info(
            "No results yet. Run a search in the New Search tab first."
        )
    else:
        st.subheader("Outreach pitches for top leads (score ≥ 50)")
        st.warning(
            "Check Companies House before emailing. Sole traders and "
            "partnerships need prior consent for marketing email (PECR)."
        )

        top_leads = active_leads[active_leads["score"] >= 50].sort_values("score", ascending=False)
        st.caption(f"{len(top_leads)} lead(s) qualify (score ≥ 50, max 20 shown).")

        if len(top_leads) == 0:
            st.info("No leads scored 50 or higher in the last search.")
        else:
            for _, lead in top_leads.head(20).iterrows():
                css_class, badge_label = STATUS_BADGE.get(lead["website_status"], ("status-unknown", lead["website_status"]))
                with st.expander(f"{lead['name']}  —  score {lead['score']}"):
                    st.markdown(
                        f'<span class="status-pill {css_class}">{badge_label}</span> '
                        f'&nbsp;&nbsp;<span style="color:#898781; font-size:13px;">{lead["address"]}</span>',
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    pitch_text = build_fallback_pitch(lead)
                    st.write(pitch_text)
                    st.code(pitch_text, language=None)
