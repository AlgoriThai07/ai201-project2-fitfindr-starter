from tools import search_listings, suggest_outfit, create_fit_card, compare_prices
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe, load_listings

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

def test_create_fit_card_happy_path():
    new_item = {
        "id": "lst_006",
        "title": "Graphic Tee",
        "description": "Vintage bootleg tee.",
        "category": "tops",
        "price": 24.00,
        "size": "L",
        "platform": "depop"
    }
    outfit = {
        "items": [],
        "description": "Pair it with wide leg jeans and white sneakers."
    }
    caption = create_fit_card(outfit, new_item)
    assert isinstance(caption, str)
    assert len(caption) > 0
    # The caption should contain key terms naturally
    assert "depop" in caption.lower()
    assert "24" in caption.lower()

def test_create_fit_card_variance():
    new_item = {
        "id": "lst_006",
        "title": "Graphic Tee",
        "description": "Vintage bootleg tee.",
        "category": "tops",
        "price": 24.00,
        "size": "L",
        "platform": "depop"
    }
    outfit = {
        "items": [],
        "description": "Pair it with wide leg jeans and white sneakers."
    }
    caption1 = create_fit_card(outfit, new_item)
    caption2 = create_fit_card(outfit, new_item)
    # They should vary due to high temperature
    assert caption1 != caption2

def test_create_fit_card_empty_guard():
    new_item = {
        "id": "lst_006",
        "title": "Graphic Tee",
        "description": "Vintage bootleg tee.",
        "category": "tops",
        "price": 24.00,
        "size": "L",
        "platform": "depop"
    }
    error_caption1 = create_fit_card("", new_item)
    error_caption2 = create_fit_card({}, new_item)
    
    assert "error" in error_caption1.lower()
    assert "error" in error_caption2.lower()

def test_compare_prices_deal():
    listings = load_listings()
    test_item = {
        "id": "test_001",
        "title": "Cheap Jeans",
        "category": "bottoms",
        "price": 10.00,
        "style_tags": ["vintage"]
    }
    result = compare_prices(test_item, listings)
    assert result is not None
    assert result["deal_rating"] == "Good Deal"
    assert result["average_price"] > 10.00
    assert result["difference_percent"] < 0

def test_compare_prices_overpriced():
    listings = load_listings()
    test_item = {
        "id": "test_002",
        "title": "Expensive Jeans",
        "category": "bottoms",
        "price": 500.00,
        "style_tags": ["vintage"]
    }
    result = compare_prices(test_item, listings)
    assert result is not None
    assert result["deal_rating"] == "Overpriced"
    assert result["difference_percent"] > 0

def test_compare_prices_no_comparable():
    result = compare_prices({"id": "test_003", "category": "random_category", "price": 50.0}, [])
    assert result is None



