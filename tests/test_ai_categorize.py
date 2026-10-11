from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_categorize_none_returns_fallback():
    with patch("backend.api.ai.generate", return_value=None):
        response = client.post("/ai/categorize", json={"title": "Taxi to airport"})
        assert response.status_code == 200
        assert response.json() == {"category": "travel"}

        response = client.post("/ai/categorize", json={"title": "Pizza and beer"})
        assert response.status_code == 200
        assert response.json() == {"category": "food"}

        response = client.post("/ai/categorize", json={"title": "Hilton hotel room"})
        assert response.status_code == 200
        assert response.json() == {"category": "hotel"}

        response = client.post("/ai/categorize", json={"title": "Louvre museum pass"})
        assert response.status_code == 200
        assert response.json() == {"category": "activities"}

        response = client.post("/ai/categorize", json={"title": "Souvenirs and clothes"})
        assert response.status_code == 200
        assert response.json() == {"category": "shopping"}

        response = client.post("/ai/categorize", json={"title": "Miscellaneous expense"})
        assert response.status_code == 200
        assert response.json() == {"category": "food"}

def test_categorize_exception_returns_fallback():
    with patch("backend.api.ai.generate", side_effect=Exception("Gemini quota exceeded")):
        response = client.post("/ai/categorize", json={"title": "Uber ride downtown"})
        assert response.status_code == 200
        assert response.json() == {"category": "travel"}

def test_categorize_valid_string_cleaned():
    with patch("backend.api.ai.generate", return_value='  "Travel". '):
        response = client.post("/ai/categorize", json={"title": "Flight ticket"})
        assert response.status_code == 200
        assert response.json() == {"category": "travel"}

def test_categorize_dict_response():
    with patch("backend.api.ai.generate", return_value={"category": "hotel"}):
        response = client.post("/ai/categorize", json={"title": "Luxury Suite"})
        assert response.status_code == 200
        assert response.json() == {"category": "hotel"}

def test_categorize_empty_title():
    response = client.post("/ai/categorize", json={"title": "   "})
    assert response.status_code == 200
    assert response.json() == {"category": "food"}
