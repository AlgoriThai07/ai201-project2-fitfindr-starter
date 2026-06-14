"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:     The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        A tuple of three strings:
            (listing_text, outfit_suggestion, fit_card)
        Each string maps to one of the three output panels in the UI.
    """
    # 1. Guard against an empty query
    user_query = user_query.strip() if user_query else ""
    if not user_query:
        return "Error: Please enter a description of what you are looking for.", "", ""

    # 2. Select the wardrobe based on wardrobe_choice
    if wardrobe_choice == "Example wardrobe":
        wardrobe = get_example_wardrobe()
    else:
        wardrobe = get_empty_wardrobe()

    # 3. Call run_agent() with the query and selected wardrobe
    session = run_agent(user_query, wardrobe)

    # 4. If session["error"] is set, return the error in the first panel and empty strings
    if session.get("error"):
        error_msg = session["error"]
        if session.get("fallback_adjusted"):
            error_msg = f"⚠️ {session['fallback_adjusted']}\n\n🛑 {error_msg}"
        else:
            error_msg = f"🛑 {error_msg}"
        return error_msg, "", ""

    # 5. Format session["selected_item"] into a readable listing_text
    item = session.get("selected_item")
    if not item:
        return "Error: No item selected by the agent.", "", ""

    title = item.get("title", "Unknown Title")
    brand = item.get("brand") or "Generic"
    size = item.get("size", "N/A")
    condition = item.get("condition", "N/A")
    price = item.get("price", 0.0)
    platform = item.get("platform", "N/A")
    description = item.get("description", "")
    colors = ", ".join(item.get("colors", []))
    tags = ", ".join(item.get("style_tags", []))

    # Format price comparison metrics if available
    price_info = ""
    comp = session.get("price_comparison")
    if comp:
        rating = comp.get("deal_rating", "Fair Price")
        diff = comp.get("difference_percent", 0.0)
        avg = comp.get("average_price", 0.0)
        if diff < 0:
            price_info = f"💰 Deal Rating: {rating} ({abs(diff)}% cheaper than comparable average of ${avg:.2f})"
        elif diff > 0:
            price_info = f"💰 Deal Rating: {rating} ({diff}% more expensive than comparable average of ${avg:.2f})"
        else:
            price_info = f"💰 Deal Rating: {rating} (Matches comparable average of ${avg:.2f})"
    else:
        price_info = "💰 Deal Rating: No comparable items found to rate price."

    fallback_note = ""
    if session.get("fallback_adjusted"):
        fallback_note = f"⚠️ Note: {session['fallback_adjusted']}\n\n"

    listing_text = (
        f"{fallback_note}"
        f"🛍️ Title: {title}\n"
        f"🏷️ Brand: {brand}\n"
        f"📏 Size: {size} | 👕 Condition: {condition}\n"
        f"💵 Price: ${price:.2f} on {platform.capitalize()}\n"
        f"{price_info}\n\n"
        f"🎨 Colors: {colors}\n"
        f"✨ Style Tags: {tags}\n\n"
        f"📝 Description: {description}"
    )

    # Format outfit suggestion
    outfit = session.get("outfit_suggestion")
    if not outfit or not isinstance(outfit, dict):
        outfit_text = "No styling suggestion could be generated."
    else:
        stylist_notes = outfit.get("description", "No styling notes provided.")
        items_list = outfit.get("items", [])
        
        # Build recommended items list
        formatted_items = []
        for idx, outfit_item in enumerate(items_list, 1):
            if outfit_item.get("id") == item.get("id"):
                formatted_items.append(
                    f"🔥 Find #{idx}: {outfit_item.get('title', 'This listing')} (${outfit_item.get('price', 0.0):.2f})"
                )
            else:
                formatted_items.append(
                    f"👖 Wardrobe #{idx}: {outfit_item.get('name', 'Wardrobe piece')} ({outfit_item.get('category', 'item')})"
                )
        
        items_text = "\n".join(formatted_items)
        outfit_text = (
            f"👩‍🎤 Stylist Recommendations:\n"
            f"{stylist_notes}\n\n"
            f"📦 Items in this look:\n"
            f"{items_text}"
        )

    # Fit card caption
    fit_card_text = session.get("fit_card") or "No fit card was generated."

    return listing_text, outfit_text, fit_card_text


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
