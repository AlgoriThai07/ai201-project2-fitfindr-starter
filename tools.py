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

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation
    return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    return ""
