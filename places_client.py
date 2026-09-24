"""Talks to the Google Places API (New) to find businesses by search text.

Loads the API key from a local .env file. Never prints or logs the key.
"""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.businessStatus",
        "places.primaryType",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "nextPageToken",
    ]
)

# Short pause between pages so we don't hammer the API while waiting for
# the next page token to become valid.
PAGE_PAUSE_SECONDS = 2


class PlacesApiError(Exception):
    """Raised when the Places API returns an error we can't recover from."""


def _get_api_key(override: str | None = None) -> str:
    """Read the API key from the environment.

    An explicit override (e.g. typed into a UI field) takes priority over
    the .env file, so callers aren't forced to use the developer's own key.

    Raises PlacesApiError with a friendly message if none is found. The key
    itself is never included in any error message or log.
    """
    api_key = override or os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise PlacesApiError(
            "No API key found. Create a .env file with "
            "GOOGLE_PLACES_API_KEY=your-key-here (see .env.example), or "
            "enter one in the app."
        )
    return api_key


def _place_to_lead(place: dict[str, Any]) -> dict[str, Any]:
    """Convert one raw Places API result into our simple lead dict.

    Missing fields become None instead of raising an error, since the
    demo key does not return ratings, reviews, or photos.
    """
    return {
        "place_id": place.get("id"),
        "name": place.get("displayName", {}).get("text"),
        "address": place.get("formattedAddress"),
        "phone": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "status": place.get("businessStatus"),
        "category": place.get("primaryType"),
        "maps_url": place.get("googleMapsUri"),
        "rating": place.get("rating"),
        "reviews": place.get("userRatingCount"),
    }


def search_places(
    query: str, max_pages: int = 3, request_limit: int = 10,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Search Google Places (New) for businesses matching a text query.

    Args:
        query: what to search for, e.g. "hair salon in Manchester, UK".
        max_pages: stop paginating after this many pages of results.
        request_limit: hard cap on the number of API requests this call
            will make, no matter what max_pages says. Protects the demo
            key's daily quota.
        api_key: optional override, e.g. a key typed into a UI field.
            Falls back to GOOGLE_PLACES_API_KEY from .env if omitted.

    Returns:
        A list of simple lead dicts (see _place_to_lead). Returns as many
        results as were fetched before hitting a limit or running out of
        pages, even if an error occurs partway through.

    Raises:
        PlacesApiError: for a missing/invalid key, quota exhaustion, or a
            network problem, with a friendly explanation.
    """
    api_key = _get_api_key(api_key)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    leads: list[dict[str, Any]] = []
    page_token: str | None = None
    requests_made = 0

    for page_number in range(max_pages):
        if requests_made >= request_limit:
            break

        body: dict[str, Any] = {"textQuery": query, "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token

        try:
            response = requests.post(
                SEARCH_URL, headers=headers, json=body, timeout=10
            )
        except requests.exceptions.RequestException as error:
            raise PlacesApiError(
                f"Network problem while contacting the Places API: {error}"
            ) from error

        requests_made += 1

        if response.status_code == 401 or response.status_code == 403:
            raise PlacesApiError(
                "The API key was rejected (invalid key or missing "
                "permissions). Check GOOGLE_PLACES_API_KEY in your .env file."
            )
        if response.status_code == 429:
            raise PlacesApiError(
                "Quota exceeded (RESOURCE_EXHAUSTED). You've hit the demo "
                "key's request limit for today. Try again tomorrow, or "
                "reduce how many searches you run."
            )
        if response.status_code != 200:
            raise PlacesApiError(
                f"Places API returned an unexpected error "
                f"(HTTP {response.status_code}): {response.text[:200]}"
            )

        data = response.json()
        for place in data.get("places", []):
            leads.append(_place_to_lead(place))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        if page_number < max_pages - 1 and requests_made < request_limit:
            time.sleep(PAGE_PAUSE_SECONDS)

    return leads


if __name__ == "__main__":
    print("Test mode: searching 'hair salon in Manchester, UK'...")
    try:
        results = search_places(
            "hair salon in Manchester, UK", max_pages=3, request_limit=3
        )
    except PlacesApiError as error:
        print(f"Error: {error}")
    else:
        print(f"Found {len(results)} businesses:")
        for lead in results:
            print(f"- {lead['name']} | {lead['address']} | {lead['website']}")
