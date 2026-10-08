from fastapi import APIRouter, HTTPException, Body
from typing import Optional
from pydantic import BaseModel, Field

from backend.services.storage.template_store import (
    load_all_templates,
    get_template,
    save_template_from_trip,
    create_trip_from_template,
    delete_template,
)

router = APIRouter(
    prefix="/templates",
    tags=["Trip Templates"]
)


class CreateTemplateRequest(BaseModel):
    name: Optional[str] = Field(default="", description="Optional custom name for template")
    description: Optional[str] = Field(default="", description="Optional template description")
    category: Optional[str] = Field(default="General", description="Category of template (e.g., Adventure, Heritage, Weekend)")


class CreateTripFromTemplateRequest(BaseModel):
    source: Optional[str] = Field(default=None, description="Optional override for origin city")
    travel_mode: Optional[str] = Field(default=None, description="Optional override for travel mode")
    budget: Optional[float] = Field(default=None, description="Optional override for total budget")


@router.get("")
@router.get("/")
def list_templates():
    """
    List all available reusable trip templates.
    Returns template metadata, preferences, and itinerary structure.
    """
    templates = load_all_templates()
    # Return templates with light metadata for faster list rendering
    summary_list = []
    for t in templates:
        summary_list.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "description": t.get("description"),
            "category": t.get("category", "General"),
            "source_trip_id": t.get("source_trip_id"),
            "created_at": t.get("created_at"),
            "destination": t.get("destination"),
            "source": t.get("source"),
            "duration_days": t.get("duration_days"),
            "travel_mode": t.get("travel_mode"),
            "preferences": t.get("preferences", []),
            "budget_summary": t.get("budget_summary", {}),
            "route_summary": t.get("route_summary", {}),
            "itinerary_structure": t.get("itinerary_structure", {}),
        })
    return {"templates": summary_list}


@router.get("/{template_id}")
def get_template_details(template_id: str):
    """
    Get full details for a specific reusable template.
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/from-trip/{trip_id}")
def create_template_from_trip_endpoint(
    trip_id: str,
    payload: CreateTemplateRequest = Body(default_factory=CreateTemplateRequest)
):
    """
    Convert an existing saved trip into a reusable template.
    Validates trip existence and extracts planning information.
    """
    try:
        template = save_template_from_trip(
            trip_id=trip_id,
            name=payload.name or "",
            description=payload.description or "",
            category=payload.category or "General"
        )
        return {
            "message": "Template created successfully",
            "template_id": template["id"],
            "name": template["name"],
            "destination": template["destination"],
            "duration_days": template["duration_days"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.post("/{template_id}/create-trip")
def instantiate_trip_from_template(
    template_id: str,
    payload: CreateTripFromTemplateRequest = Body(default_factory=CreateTripFromTemplateRequest)
):
    """
    Create a new trip from an existing template.
    Guarantees the original trip and template remain completely unmodified.
    """
    try:
        overrides = {}
        if payload.source is not None:
            overrides["source"] = payload.source
        if payload.travel_mode is not None:
            overrides["travel_mode"] = payload.travel_mode
        if payload.budget is not None:
            overrides["budget"] = payload.budget

        new_trip_id, _ = create_trip_from_template(
            template_id=template_id,
            overrides=overrides
        )

        template = get_template(template_id)

        return {
            "message": "New trip created successfully from template",
            "trip_id": new_trip_id,
            "template_id": template_id,
            "template_name": template.get("name") if template else "Template",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create trip from template: {str(e)}")


@router.delete("/{template_id}")
def remove_template(template_id: str):
    """
    Delete a reusable template.
    """
    deleted = delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully", "template_id": template_id}
