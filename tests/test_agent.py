import pytest
from agent import run_agent, _new_session
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


def test_session_initialization():
    wardrobe = get_example_wardrobe()
    session = _new_session("test query", wardrobe)
    
    assert session["query"] == "test query"
    assert session["parsed"] == {}
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["price_comparison"] is None
    assert session["wardrobe"] == wardrobe
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    assert session["fallback_adjusted"] is None
    assert session["error"] is None


def test_agent_happy_path_state_flow():
    # A query that has matching results
    query = "vintage graphic tee under $30"
    wardrobe = get_example_wardrobe()
    
    session = run_agent(query, wardrobe)
    
    assert session["error"] is None
    assert session["parsed"] != {}
    assert "description" in session["parsed"]
    
    # Verify search results
    assert len(session["search_results"]) > 0
    assert session["selected_item"] is not None
    assert session["selected_item"] == session["search_results"][0]
    
    # Check that price comparison was computed
    assert session["price_comparison"] is not None
    assert "deal_rating" in session["price_comparison"]
    
    # Verify outfit suggestion state flow
    assert session["outfit_suggestion"] is not None
    assert isinstance(session["outfit_suggestion"], dict)
    assert "items" in session["outfit_suggestion"]
    assert "description" in session["outfit_suggestion"]
    
    # Assert that the new item is present in the outfit's items list
    outfit_items = session["outfit_suggestion"]["items"]
    assert any(item["id"] == session["selected_item"]["id"] for item in outfit_items if "id" in item)
    
    # Verify fit card generation
    assert session["fit_card"] is not None
    assert isinstance(session["fit_card"], str)
    assert len(session["fit_card"]) > 0


def test_agent_no_results_early_exit():
    # A query that should yield no listings, even after broadening
    query = "designer ballgown size XXS under $5"
    wardrobe = get_example_wardrobe()
    
    session = run_agent(query, wardrobe)
    
    assert session["error"] is not None
    assert "No listings found matching" in session["error"]
    
    # Verify state: early exit must leave downstream keys as None
    assert session["selected_item"] is None
    assert session["price_comparison"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    # Verify we attempted fallback
    assert session["fallback_adjusted"] is not None
    assert "No results for original filters" in session["fallback_adjusted"]


def test_agent_fallback_search_success():
    # A query that fails initially but succeeds after relaxing filters.
    # We want a query that has no listings matching the specific price or size, but matches description.
    # In listings.json, let's search for "combat boots" but with a very low max price ($10).
    # The combat boots (lst_008) are $45.
    # Initially: "combat boots under $10" -> no results.
    # Fallback: remove size (already none) and increase price by 25% ($12.50) -> still no results.
    # Let's search with size "XXS" for "vintage graphic tee under $30".
    # There is a vintage graphic tee (lst_006) which is size "L" and price $24.
    # Query: "vintage graphic tee size XXS under $30"
    # Initially: description="vintage graphic tee", size="XXS", price=30 -> 0 results (since size is L).
    # Fallback: remove size, increase price by 25% (to $37.50) -> description="vintage graphic tee", size=None, price=37.50
    # This should find the size L tee (since L is found under no size filter, and price 24 <= 37.50).
    
    query = "vintage graphic tee size XXS under $30"
    wardrobe = get_example_wardrobe()
    
    session = run_agent(query, wardrobe)
    
    assert session["error"] is None
    assert session["fallback_adjusted"] is not None
    assert "removing size filter" in session["fallback_adjusted"]
    assert "increasing max price by 25%" in session["fallback_adjusted"]
    
    assert session["selected_item"] is not None
    assert session["selected_item"]["size"] == "L"  # original filter size XXS was relaxed
    assert session["fit_card"] is not None
