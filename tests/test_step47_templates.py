import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import copy
from starlette.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import load_all_trips, load_trip


client = TestClient(app)

def test_trip_templates_lifecycle():
    # 1. Fetch existing trips
    trips = load_all_trips()
    assert len(trips) > 0, "Expected at least one trip in database for template tests"
    source_trip = trips[0]
    source_trip_id = source_trip["id"]
    original_trip_snapshot = copy.deepcopy(source_trip["data"])

    # 2. Convert saved trip to template
    tpl_payload = {
        "name": "Test Weekend Escape",
        "description": "A reusable weekend escape template",
        "category": "Weekend"
    }
    res = client.post(f"/templates/from-trip/{source_trip_id}", json=tpl_payload)
    assert res.status_code == 200, f"Failed to create template: {res.text}"
    data = res.json()
    assert "template_id" in data
    template_id = data["template_id"]
    assert data["name"] == "Test Weekend Escape"

    # Also test the alternative endpoint /trip/{trip_id}/template
    res_alt = client.post(f"/trip/{source_trip_id}/template", json={"name": "Alt Template"})
    assert res_alt.status_code == 200, f"Alternative endpoint failed: {res_alt.text}"
    alt_template_id = res_alt.json()["template_id"]

    # 3. List templates
    res_list = client.get("/templates")
    assert res_list.status_code == 200
    templates = res_list.json().get("templates", [])
    assert any(t["id"] == template_id for t in templates), "Created template not found in list"

    # Verify template metadata fields required by Step 47:
    created_tpl_meta = next(t for t in templates if t["id"] == template_id)
    assert "destination" in created_tpl_meta
    assert "duration_days" in created_tpl_meta
    assert "travel_mode" in created_tpl_meta
    assert "preferences" in created_tpl_meta
    assert "itinerary_structure" in created_tpl_meta
    print("Template metadata verified:", created_tpl_meta["destination"], created_tpl_meta["duration_days"], "days")

    # 4. Get template details
    res_detail = client.get(f"/templates/{template_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == template_id
    assert "template_data" in detail

    # 5. Create new trip from template with optional override
    create_res = client.post(
        f"/templates/{template_id}/create-trip",
        json={"source": "Custom Origin", "travel_mode": "car"}
    )
    assert create_res.status_code == 200, f"Failed to create trip from template: {create_res.text}"
    create_data = create_res.json()
    assert "trip_id" in create_data
    new_trip_id = create_data["trip_id"]
    assert new_trip_id != source_trip_id, "New trip ID must be distinct from source trip ID"

    # 6. Verify newly created trip loads properly
    res_new_trip = client.get(f"/trip/{new_trip_id}")
    assert res_new_trip.status_code == 200, f"New trip failed to load: {res_new_trip.text}"
    new_trip_obj = res_new_trip.json()
    assert new_trip_obj.get("trip", {}).get("source") == "Custom Origin"
    assert "spawned_from_template" in new_trip_obj.get("trip", {})
    assert new_trip_obj.get("trip", {}).get("spawned_from_template", {}).get("template_id") == template_id

    # 7. CRITICAL: Verify source trip was NOT modified
    after_source_trip_data = load_trip(source_trip_id)
    assert after_source_trip_data == original_trip_snapshot, "CRITICAL ERROR: Original source trip was mutated!"
    print("Original trip unchanged verification passed!")

    # 8. Test error handling
    res_nonexistent = client.post("/templates/nonexistent-id/create-trip", json={})
    assert res_nonexistent.status_code == 404

    res_invalid_source = client.post("/templates/from-trip/nonexistent-trip-id", json={})
    assert res_invalid_source.status_code == 404

    # 9. Clean up test templates
    del_res1 = client.delete(f"/templates/{template_id}")
    assert del_res1.status_code == 200
    del_res2 = client.delete(f"/templates/{alt_template_id}")
    assert del_res2.status_code == 200

    print("Step 47 Trip Templates all backend tests PASSED successfully!")

if __name__ == "__main__":
    test_trip_templates_lifecycle()
