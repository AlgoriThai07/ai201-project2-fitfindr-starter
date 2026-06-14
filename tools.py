"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    import re

    # Helper function for matching sizes
    def size_matches(query_size: str, listing_size: str) -> bool:
        q = query_size.lower().strip()
        l = listing_size.lower().strip()
        if q in l or l in q:
            return True
        # Common aliases
        aliases = {
            "m": ["medium", "med", "mediums"],
            "s": ["small", "sml", "smalls"],
            "l": ["large", "lrg", "larges"],
            "xl": ["extra large", "extra-large"],
        }
        for key, vals in aliases.items():
            if q == key and any(v in l for v in vals):
                return True
            if q in vals and key in l:
                return True
        return False

    # 1. Load all listings
    all_listings = load_listings()
    filtered_listings = []

    # 2. Filter by max_price and size
    for item in all_listings:
        if max_price is not None and item.get("price", 0.0) > max_price:
            continue
        if size is not None and not size_matches(size, item.get("size", "")):
            continue
        filtered_listings.append(item)

    # 3. Score each remaining listing by keyword overlap with description
    query_words = set(re.findall(r"\w+", description.lower()))
    if not query_words:
        return []

    scored_listings = []
    for item in filtered_listings:
        title_lower = item.get("title", "").lower()
        desc_lower = item.get("description", "").lower()
        style_tags = [tag.lower() for tag in item.get("style_tags", [])]

        score = 0
        for word in query_words:
            # Check for matches in title, style tags, and description
            if word in title_lower:
                score += 3
            if any(word in tag for tag in style_tags):
                score += 2
            if word in desc_lower:
                score += 1

        # 4. Drop any listings with a score of 0
        if score > 0:
            scored_listings.append((score, item))

    # 5. Sort by score, highest first, and return listing dicts
    scored_listings.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> dict:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A dictionary containing:
        - 'items' (list[dict]): Selected wardrobe items + the new item.
        - 'description' (str): Detailed outfit suggestions and styling tips.
    """
    import json

    wardrobe_items = wardrobe.get("items", [])
    client = _get_groq_client()

    system_prompt = (
        "You are a professional fashion stylist. Given a new secondhand clothing item and the user's current wardrobe, "
        "your goal is to suggest 1-2 complete outfits.\n"
        "You must return a JSON object with exactly two keys:\n"
        "1. \"items\": A list of dictionaries. This list must include the exact dictionaries of the selected "
        "wardrobe items, plus the new_item dictionary itself.\n"
        "2. \"description\": A detailed text description (string) of the outfit combinations, including styling tips, "
        "vibes, and how to wear them.\n\n"
        "If the wardrobe items list is empty, set \"items\" to a list containing only the new_item dictionary, and "
        "provide general styling and pairing advice in the \"description\"."
    )

    user_prompt = f"""
New Item:
{json.dumps(new_item, indent=2)}

User Wardrobe Items:
{json.dumps(wardrobe_items, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Basic validations
        if "items" not in result or not isinstance(result["items"], list):
            result["items"] = [new_item]
        if "description" not in result:
            result["description"] = "Try styling this item with classic basics."

        return result
    except Exception as e:
        # Fallback styling recommendation on any error
        return {
            "items": [new_item],
            "description": f"Styled with basic pieces. Vibe: casual classic. Try styling this {new_item.get('title', 'clothing piece')} with standard denim and neutral shoes."
        }


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: dict | str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion (dict or string) from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.
    """
    # 1. Guard against empty/missing inputs
    if not outfit:
        return "Error: Could not generate a fit card due to missing outfit details."

    description = ""
    if isinstance(outfit, dict):
        description = outfit.get("description", "").strip()
    elif isinstance(outfit, str):
        description = outfit.strip()

    if not description:
        return "Error: Could not generate a fit card due to empty styling suggestions."

    title = new_item.get("title", "thrift find")
    price = new_item.get("price", "great price")
    platform = new_item.get("platform", "thrift shop")

    client = _get_groq_client()

    system_prompt = (
        "You are a trendy social media content creator writing a short, casual, and authentic "
        "OOTD caption (Instagram/TikTok style) showcasing a thrifted find.\n\n"
        "Guidelines:\n"
        "- Write exactly 2-4 sentences.\n"
        "- Make it feel casual, aesthetic, and conversational (lowercase style, minor emojis, real slang, NOT a product description).\n"
        "- You MUST naturally mention the item title, price, and platform exactly once each.\n"
        "- Incorporate the styling suggestion/vibe naturally."
    )

    user_prompt = f"""
New Item Details:
- Title: {title}
- Price: ${price}
- Platform: {platform}
- Description: {new_item.get('description', '')}

Styling Suggestion:
{description}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # Use high temperature to ensure different captions each time
            temperature=1.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Fallback caption that includes all required fields
        return f"obsessed with my new {title} from {platform} for ${price}! styling it with some neutral basics today 🖤"


# ── Tool 4: compare_prices [STRETCH] ──────────────────────────────────────────

def compare_prices(new_item: dict, listings: list[dict]) -> dict | None:
    """
    Compare the price of the selected item with the average price of comparable
    listings in the dataset (matching the same category and style tags).

    Args:
        new_item: The selected listing dict.
        listings: The full list of listing dicts to compare against.

    Returns:
        A dict with comparison statistics, or None if no comparable items exist.
    """
    category = new_item.get("category", "")
    style_tags = {t.lower() for t in new_item.get("style_tags", [])}
    new_item_id = new_item.get("id")

    # 1. Try to find items in the same category sharing at least one style tag (excluding the new item itself)
    comparable = [
        item for item in listings
        if item.get("category") == category
        and item.get("id") != new_item_id
        and any(t.lower() in style_tags for t in item.get("style_tags", []))
    ]

    # 2. Fall back to matching only by category if no style tag matches are found
    if not comparable:
        comparable = [
            item for item in listings
            if item.get("category") == category
            and item.get("id") != new_item_id
        ]

    if not comparable:
        return None

    # 3. Calculate statistics
    avg_price = sum(item.get("price", 0.0) for item in comparable) / len(comparable)
    new_price = new_item.get("price", 0.0)

    if avg_price > 0:
        diff_pct = ((new_price - avg_price) / avg_price) * 100
    else:
        diff_pct = 0.0

    # 4. Rating threshold
    if diff_pct <= -10.0:
        deal_rating = "Good Deal"
    elif diff_pct >= 10.0:
        deal_rating = "Overpriced"
    else:
        deal_rating = "Fair Price"

    return {
        "average_price": round(avg_price, 2),
        "difference_percent": round(diff_pct, 1),
        "deal_rating": deal_rating
    }
