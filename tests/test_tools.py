from tools import search_listings

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

