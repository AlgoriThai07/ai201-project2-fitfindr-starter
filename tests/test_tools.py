from tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_matching():
    # Test case insensitivity and partial matching
    results_m = search_listings("tee", size="m", max_price=None)
    # Check that it returns items containing 'm' in size (like 'S/M' or 'M')
    for item in results_m:
        sz = item["size"].lower()
        assert "m" in sz or "medium" in sz

def test_search_keyword_sorting():
    # A query like "Vintage Levi's Jeans" should score higher for vintage Levis
    results = search_listings("Vintage Levi's Jeans", size=None, max_price=None)
    assert len(results) > 0
    # The first item should contain the most overlapping keywords (e.g. "Vintage", "Levi's", "Jeans")
    top_item = results[0]
    assert "vintage" in top_item["title"].lower() or "levi" in top_item["title"].lower()

def test_suggest_outfit_happy_path():
    new_item = {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit.",
        "category": "tops",
        "price": 24.00,
        "size": "L"
    }
    wardrobe = get_example_wardrobe()
    outfit = suggest_outfit(new_item, wardrobe)
    
    assert isinstance(outfit, dict)
    assert "items" in outfit
    assert "description" in outfit
    assert isinstance(outfit["items"], list)
    assert len(outfit["items"]) > 0
    assert any(item["id"] == new_item["id"] for item in outfit["items"] if "id" in item)
    assert isinstance(outfit["description"], str)
    assert len(outfit["description"]) > 0

def test_suggest_outfit_empty_wardrobe():
    new_item = {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit.",
        "category": "tops",
        "price": 24.00,
        "size": "L"
    }
    wardrobe = get_empty_wardrobe()
    outfit = suggest_outfit(new_item, wardrobe)
    
    assert isinstance(outfit, dict)
    assert "items" in outfit
    assert "description" in outfit
    assert len(outfit["items"]) == 1
    assert outfit["items"][0]["id"] == new_item["id"]
    assert isinstance(outfit["description"], str)
    assert len(outfit["description"]) > 0


