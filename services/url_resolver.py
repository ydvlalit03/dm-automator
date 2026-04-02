import logging
import re

import httpx

logger = logging.getLogger(__name__)

# Matches Instagram post/reel URLs and extracts shortcode
URL_PATTERN = re.compile(
    r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)"
)

IG_GRAPH_URL = "https://graph.facebook.com/v21.0"


def extract_shortcode(url: str) -> str | None:
    """Extract shortcode from an Instagram post/reel URL."""
    match = URL_PATTERN.search(url.strip())
    return match.group(1) if match else None


def detect_post_type(url: str) -> str:
    """Detect if URL is a reel, post, or tv."""
    if "/reel/" in url:
        return "reel"
    if "/tv/" in url:
        return "tv"
    return "post"


async def resolve_media_id(
    shortcode: str,
    ig_business_account_id: str,
    access_token: str,
) -> dict:
    """
    Resolve a shortcode to a Media ID via Instagram Graph API.

    Uses the business_discovery approach to find media by iterating
    through recent media. For the user's own account, we search their media.

    Returns: {"media_id": str, "caption": str} or {"error": str}
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch recent media and find the one matching the shortcode
        # We paginate through media to find the shortcode
        url = f"{IG_GRAPH_URL}/{ig_business_account_id}/media"
        params = {
            "fields": "id,shortcode,caption,media_type,timestamp",
            "limit": 50,
            "access_token": access_token,
        }

        pages_checked = 0
        max_pages = 10  # Check up to 500 posts

        while pages_checked < max_pages:
            try:
                resp = await client.get(url, params=params)
                data = resp.json()

                if resp.status_code != 200:
                    error = data.get("error", {}).get("message", str(data))
                    logger.error("Graph API error: %s", error)
                    return {"error": error}

                for media in data.get("data", []):
                    if media.get("shortcode") == shortcode:
                        return {
                            "media_id": media["id"],
                            "caption": media.get("caption", ""),
                        }

                # Check next page
                paging = data.get("paging", {})
                next_url = paging.get("next")
                if not next_url:
                    break

                url = next_url
                params = {}  # next_url already has params
                pages_checked += 1

            except Exception as e:
                logger.exception("Error resolving media ID for shortcode %s", shortcode)
                return {"error": str(e)}

    return {"error": f"Post with shortcode '{shortcode}' not found in your recent media (checked {pages_checked * 50} posts)"}


async def bulk_resolve(
    urls: list[str],
    ig_business_account_id: str,
    access_token: str,
) -> list[dict]:
    """
    Resolve multiple Instagram URLs to Media IDs.
    Returns list of {"url", "shortcode", "post_type", "media_id", "caption", "error"}.
    """
    results = []

    # First, fetch all media in one go to avoid repeated API calls
    all_media = {}
    async with httpx.AsyncClient(timeout=30) as client:
        api_url = f"{IG_GRAPH_URL}/{ig_business_account_id}/media"
        params = {
            "fields": "id,shortcode,caption,media_type,timestamp",
            "limit": 50,
            "access_token": access_token,
        }

        pages_checked = 0
        while pages_checked < 10:
            try:
                resp = await client.get(api_url, params=params)
                data = resp.json()
                if resp.status_code != 200:
                    break

                for media in data.get("data", []):
                    sc = media.get("shortcode")
                    if sc:
                        all_media[sc] = {
                            "media_id": media["id"],
                            "caption": media.get("caption", ""),
                        }

                next_url = data.get("paging", {}).get("next")
                if not next_url:
                    break
                api_url = next_url
                params = {}
                pages_checked += 1
            except Exception:
                break

    # Now match URLs to fetched media
    for url in urls:
        url = url.strip()
        if not url:
            continue

        shortcode = extract_shortcode(url)
        if not shortcode:
            results.append({
                "url": url,
                "shortcode": None,
                "post_type": "unknown",
                "media_id": None,
                "caption": None,
                "error": "Invalid Instagram URL",
            })
            continue

        post_type = detect_post_type(url)
        media_info = all_media.get(shortcode)

        if media_info:
            results.append({
                "url": url,
                "shortcode": shortcode,
                "post_type": post_type,
                "media_id": media_info["media_id"],
                "caption": media_info["caption"],
                "error": None,
            })
        else:
            results.append({
                "url": url,
                "shortcode": shortcode,
                "post_type": post_type,
                "media_id": None,
                "caption": None,
                "error": "Post not found in your recent media",
            })

    return results
