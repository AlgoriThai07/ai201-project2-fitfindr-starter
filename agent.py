"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import os
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card, compare_prices
from utils.data_loader import load_listings


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "price_comparison": None,    # dictionary returned by compare_prices
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # dict returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "fallback_adjusted": None,   # warning if fallback was triggered
        "error": None,               # set if the interaction ended early
    }


# ── query parsing helper ──────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _fallback_query_parser(query: str) -> dict:
    """Fallback query parser using regex if LLM is unavailable."""
    import re
    price_match = re.search(r"under\s*\$?(\d+)", query, re.IGNORECASE)
    max_price = float(price_match.group(1)) if price_match else None
    
    size_match = re.search(r"\bsize\s+(\w+)\b", query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None
    
    # Simple extraction of description by removing price and size filter keywords
    desc = query
    if price_match:
        desc = desc.replace(price_match.group(0), "")
    if size_match:
        desc = desc.replace(size_match.group(0), "")
    desc = re.sub(r"\s+", " ", desc).strip()
    
    return {
        "description": desc,
        "size": size,
        "max_price": max_price
    }


def _parse_query_with_llm(query: str) -> dict:
    """
    Use Llama 3.3 via Groq to extract structured parameters from a natural query.
    Returns a dict with 'description', 'size', and 'max_price'.
    """
    import json
    
    try:
        client = _get_groq_client()
    except ValueError:
        # If API key is not configured, fall back immediately to regex parser
        return _fallback_query_parser(query)

    system_prompt = (
        "You are an expert search query parser for a secondhand clothing platform.\n"
        "Given a user query, extract the following fields in JSON format:\n"
        "1. \"description\": Keywords representing the item described (e.g. \"vintage graphic tee\", \"track jacket\", \"combat boots\"). Always provide this as a string.\n"
        "2. \"size\": The size of the clothing if mentioned (e.g. \"M\", \"L\", \"XXS\", \"8\", \"Medium\"). If no size is mentioned, return null.\n"
        "3. \"max_price\": The maximum price the user is willing to pay as a number (float), if mentioned (e.g. if the user query says \"under $30\" or \"under 30\", return 30.0). If no max price is mentioned, return null.\n\n"
        "Ensure the output is exactly a JSON object with only these three keys: \"description\", \"size\", and \"max_price\"."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Clean and validate types
        description = parsed.get("description", "").strip()
        size = parsed.get("size")
        if size is not None:
            size = str(size).strip()
            if size.lower() == "null" or size == "":
                size = None
                
        max_price = parsed.get("max_price")
        if max_price is not None:
            try:
                max_price = float(max_price)
            except (ValueError, TypeError):
                max_price = None
                
        return {
            "description": description,
            "size": size,
            "max_price": max_price
        }
    except Exception as e:
        # Print warning but fall back gracefully
        print(f"Groq query parser exception: {e}. Falling back to regex.")
        return _fallback_query_parser(query)


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse user's query
    parsed = _parse_query_with_llm(query)
    session["parsed"] = parsed

    desc = parsed.get("description", "")
    size = parsed.get("size")
    max_price = parsed.get("max_price")

    # Ensure max_price is float or None
    if max_price is not None:
        try:
            max_price = float(max_price)
        except (ValueError, TypeError):
            max_price = None

    # Step 3: Call search_listings() with parsed parameters
    results = search_listings(desc, size=size, max_price=max_price)

    # Step 4: Search Fallback Check
    if not results:
        # Retry with relaxed criteria
        adjustments = []
        new_size = None
        new_max_price = None

        if size is not None:
            adjustments.append("removing size filter")
        if max_price is not None:
            new_max_price = max_price * 1.25
            adjustments.append(f"increasing max price by 25% to ${new_max_price:.2f}")
        
        session["fallback_adjusted"] = f"No results for original filters. Retrying search by: {', '.join(adjustments)}."
        
        # Retry search
        results = search_listings(desc, size=new_size, max_price=new_max_price)

        if not results:
            session["search_results"] = []
            session["error"] = f"No listings found matching '{desc}' even after broadening search parameters. Try using different keywords."
            return session

    # Step 5: Select top result and store all results
    session["search_results"] = results
    selected_item = results[0]
    session["selected_item"] = selected_item

    # Step 6: Price comparison (stretch goal)
    try:
        all_listings = load_listings()
        comparison = compare_prices(selected_item, all_listings)
        session["price_comparison"] = comparison
    except Exception as e:
        session["price_comparison"] = None

    # Step 7: Call suggest_outfit() with the selected item and wardrobe
    try:
        outfit = suggest_outfit(selected_item, wardrobe)
        session["outfit_suggestion"] = outfit
    except Exception as e:
        session["error"] = f"Outfit suggestion failed: {e}"
        return session

    # Step 8: Call create_fit_card() with the outfit suggestion and selected item
    try:
        fit_card = create_fit_card(outfit, selected_item)
        session["fit_card"] = fit_card
    except Exception as e:
        session["error"] = f"Fit card generation failed: {e}"
        return session

    # Step 9: Return session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import pprint
    # Reconfigure stdout to use UTF-8 to prevent encoding errors with emojis/non-ASCII chars
    sys.stdout.reconfigure(encoding='utf-8')
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Verification: Complete Interaction Flow ===")
    query = (
        "I'm looking for a vintage graphic tee under $30. "
        "I mostly wear baggy jeans and chunky sneakers. "
        "What's out there and how would I style it?"
    )
    print(f"User Query: \"{query}\"\n")
    
    session = run_agent(
        query=query,
        wardrobe=get_example_wardrobe(),
    )
    
    if session["error"]:
        print(f"Execution Error: {session['error']}")
    else:
        print("--- 1. Parsed Query Parameters ---")
        pprint.pprint(session["parsed"])
        print()

        print("--- 2. Selected Item (Dict) ---")
        pprint.pprint(session["selected_item"])
        print()

        print("--- 3. Outfit Suggestion (Dict) ---")
        pprint.pprint(session["outfit_suggestion"])
        print()

        print("--- 4. Fit Card Caption ---")
        print(session["fit_card"])
        print()

        print("--- 5. State Flow Verification ---")
        # Verify selected_item is the exact dict passed into suggest_outfit's items
        outfit_items = session["outfit_suggestion"]["items"]
        # Find the selected item within the outfit suggestion items
        passed_item = next((item for item in outfit_items if item.get("id") == session["selected_item"]["id"]), None)
        
        print(f"Selected Item ID: {session['selected_item'].get('id')}")
        print(f"Passed Item ID in Outfit Suggestion: {passed_item.get('id') if passed_item else None}")
        
        is_same_item = (passed_item == session["selected_item"])
        print(f"Is the selected item exact dict passed into suggest_outfit? {is_same_item}")
        
        # Verify outfit suggestion is what went into create_fit_card.
        print(f"Outfit Suggestion Description exists: {bool(session['outfit_suggestion'].get('description'))}")
        print(f"Fit Card generated successfully: {bool(session['fit_card'])}")

    print("\n=== Verification: No-Results Path ===")
    query2 = "designer ballgown size XXS under $5"
    print(f"User Query: \"{query2}\"\n")
    session2 = run_agent(
        query=query2,
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error Message: {session2['error']}")
    print(f"Is Fit Card None? {session2['fit_card'] is None}")
