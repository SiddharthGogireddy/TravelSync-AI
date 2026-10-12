import logging
from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel

from backend.services.auth.authorization import extract_user_id, verify_trip_access

logger = logging.getLogger(__name__)

from backend.models.trip_update import (
    TripUpdateRequest,
)
from backend.utils.helpers import normalize_place_name
from backend.services.trip_editor.prompt_parser import (
    parse_prompt,
)
from backend.services.trip_editor.explanation_service import explain_attraction
from backend.services.trip_editor.llm_interpreter import (
    interpret_trip_prompt,
)

from backend.services.storage.trip_store import (
    load_trip,
    update_saved_trip,
)

from backend.services.external.place_service import (
    find_place,
)

from backend.services.planner.budget_tracker import (
    calculate_budget,
)

from backend.services.planner.budget_replanner import (
    fit_trip_to_budget,
)

from backend.services.planner.day_regenerator import (
    regenerate_day,
)
from backend.services.planner.distance import haversine
from backend.services.planner.opening_hours_scheduler import schedule_day_opening_hours

router = APIRouter(
    prefix="/trip",
    tags=["Trip Update"],
)


def recalculate_day_transit_and_legs(day_places: list, mode_str: str = "car"):
    for idx, p in enumerate(day_places):
        if idx == 0:
            p["travel_from_previous_km"] = None
            p["travel_time_minutes"] = 0
            continue
        prev = day_places[idx - 1]
        lat1, lon1 = prev.get("lat"), prev.get("lon")
        lat2, lon2 = p.get("lat"), p.get("lon")
        if (
            lat1 is not None and lon1 is not None
            and lat2 is not None and lon2 is not None
            and (lat1 != 0 or lon1 != 0) and (lat2 != 0 or lon2 != 0)
        ):
            d = round(haversine(lat1, lon1, lat2, lon2), 2)
            if d > 0.05:
                p["travel_from_previous_km"] = d
                p["travel_time_minutes"] = max(5, int(round((d / 30.0) * 60.0)))
            else:
                p["travel_from_previous_km"] = None
                p["travel_time_minutes"] = 10
        else:
            p["travel_from_previous_km"] = None
            p["travel_time_minutes"] = 15
    try:
        updated, _ = schedule_day_opening_hours(day_places, travel_mode=mode_str)
        return updated
    except Exception:
        return day_places


@router.patch("/{trip_id}")
async def update_trip(
    trip_id: str,
    update: TripUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):

    # --------------------------------
    # Load trip & verify editor access
    # --------------------------------
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    trip = trip_record.get("data")

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    # --------------------------------
    # Updates (Prompt or direct fields)
    # --------------------------------
    parsed = {}
    if update.add_place:
        parsed["add_place"] = update.add_place
    if update.remove_place:
        parsed["remove_place"] = update.remove_place
    if update.budget is not None:
        parsed["budget"] = update.budget
    if update.regenerate_day is not None:
        parsed["regenerate_day"] = update.regenerate_day

    if update.prompt:
        # --------------------------------
        # Try LLM interpretation
        # --------------------------------
        try:
            llm_result = interpret_trip_prompt(update.prompt)
            actions = llm_result.get("actions", [])
        except Exception as e:
            logger.warning(f"LLM failed: {e}")
            actions = []

        llm_parsed = {}
        for action in actions:
            action_type = action.get("type")
            if action_type == "add_place":
                llm_parsed["add_place"] = action.get("place")
            elif action_type == "remove_place":
                llm_parsed["remove_place"] = action.get("place")
            elif action_type == "set_budget":
                llm_parsed["budget"] = action.get("amount")
            elif action_type == "regenerate_day":
                llm_parsed["regenerate_day"] = action.get("day")
            elif action_type == "set_interests":
                llm_parsed["regenerate_day"] = action.get("day")
                llm_parsed["preferred_interests"] = action.get("interests", [])

        # Fallback to deterministic parser
        if not llm_parsed:
            llm_parsed = parse_prompt(update.prompt)

        parsed.update(llm_parsed)

    if parsed:
        from backend.services.planner.distance import haversine
        from backend.services.planner.opening_hours_scheduler import schedule_day_opening_hours
        from backend.services.planner.dashboard import build_dashboard
        from backend.services.planner.trip_summary import build_summary

        def _recalculate_day_transit_and_legs(day_places: list, mode_str: str = "car"):
            for idx, p in enumerate(day_places):
                if idx == 0:
                    p["travel_from_previous_km"] = None
                    p["travel_time_minutes"] = 0
                    continue
                prev = day_places[idx - 1]
                lat1, lon1 = prev.get("lat"), prev.get("lon")
                lat2, lon2 = p.get("lat"), p.get("lon")
                if (
                    lat1 is not None and lon1 is not None
                    and lat2 is not None and lon2 is not None
                    and (lat1 != 0 or lon1 != 0) and (lat2 != 0 or lon2 != 0)
                ):
                    d = round(haversine(lat1, lon1, lat2, lon2), 2)
                    if d > 0.05:
                        p["travel_from_previous_km"] = d
                        p["travel_time_minutes"] = max(5, int(round((d / 30.0) * 60.0)))
                    else:
                        p["travel_from_previous_km"] = None
                        p["travel_time_minutes"] = 10
                else:
                    p["travel_from_previous_km"] = None
                    p["travel_time_minutes"] = 15
            try:
                updated, _ = schedule_day_opening_hours(day_places, travel_mode=mode_str)
                return updated
            except Exception:
                return day_places

        removed_from_day = None
        day_schedule = trip["trip"].get("day_schedule", {})
        travel_mode = trip["trip"].get("travel_mode", "car")

        # =================================
        # 1. REMOVE PLACE (Execute first!)
        # =================================
        if "remove_place" in parsed:
            raw_remove = str(parsed["remove_place"]).strip()
            norm_remove = normalize_place_name(raw_remove)

            generic_terms = [
                "one attraction",
                "an attraction",
                "1 attraction",
                "any attraction",
                "a place",
                "one place",
                "an activity",
                "one activity",
            ]
            is_generic = norm_remove in generic_terms or any(raw_remove.lower() == g for g in generic_terms)

            if is_generic:
                eligible_days = [d for d, pls in day_schedule.items() if len(pls) > 0]
                if eligible_days:
                    target_day = max(eligible_days, key=lambda d: len(day_schedule[d]))
                    day_places = day_schedule[target_day]
                    remove_idx = min(range(len(day_places)), key=lambda i: day_places[i].get("score", 0))
                    removed_place = day_places.pop(remove_idx)
                    removed_from_day = target_day
                    removed_name = normalize_place_name(removed_place.get("name", ""))
                    trip["trip"]["places"] = [
                        p for p in trip["trip"]["places"]
                        if normalize_place_name(p.get("name", "")) != removed_name
                    ]
                    orig_name = removed_place.get("name", "")
                    trip["trip"].setdefault("excluded_places", []).extend([orig_name, removed_name])
                    day_schedule[target_day] = _recalculate_day_transit_and_legs(day_places, travel_mode)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot remove attraction: no attractions are currently scheduled in this trip.",
                    )
            else:
                found_match = False
                for d, pls in day_schedule.items():
                    matching_indices = [
                        i for i, p in enumerate(pls)
                        if normalize_place_name(p.get("name", "")) == norm_remove
                        or norm_remove in p.get("name", "").lower()
                        or p.get("name", "").lower() in norm_remove
                    ]
                    if matching_indices:
                        found_match = True
                        removed_from_day = d
                        for idx in reversed(matching_indices):
                            pls.pop(idx)
                        day_schedule[d] = _recalculate_day_transit_and_legs(pls, travel_mode)

                matching_pool = [
                    p for p in trip["trip"].get("places", [])
                    if normalize_place_name(p.get("name", "")) == norm_remove
                    or norm_remove in p.get("name", "").lower()
                    or p.get("name", "").lower() in norm_remove
                ]
                if not found_match and not matching_pool:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot remove attraction '{raw_remove}': attraction was not found in the trip.",
                    )

                trip["trip"]["places"] = [
                    p for p in trip["trip"]["places"]
                    if normalize_place_name(p.get("name", "")) != norm_remove
                    and norm_remove not in p.get("name", "").lower()
                    and p.get("name", "").lower() not in norm_remove
                ]
                trip["trip"].setdefault("excluded_places", []).extend([raw_remove, norm_remove])

            trip["trip"]["day_schedule"] = day_schedule

        # =================================
        # 2. ADD PLACE (Execute second!)
        # =================================
        if "add_place" in parsed:
            place_name = str(parsed["add_place"]).strip()
            destination = trip["trip"]["destination_location"]

            place = await find_place(
                place_name,
                destination["lat"],
                destination["lon"],
            )

            if place is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Place '{place_name}' not found",
                )

            new_place = {
                "name": place.get("name", place_name),
                "category": (
                    place.get("kinds", "")
                    .split(",")[0]
                    .replace("_", " ")
                    .title()
                ) or "Sightseeing",
                "distance_km": round(place.get("dist", 0) / 1000, 2),
                "lat": place.get("point", {}).get("lat"),
                "lon": place.get("point", {}).get("lon"),
                "score": 0,
                "matched_travelers": [],
                "match_count": 0,
            }

            trip["trip"]["places"].append(new_place)

            if day_schedule:
                if removed_from_day and removed_from_day in day_schedule:
                    target_day = removed_from_day
                else:
                    target_day = min(day_schedule, key=lambda day: len(day_schedule[day]))

                day_schedule[target_day].append(new_place)
                day_schedule[target_day] = _recalculate_day_transit_and_legs(day_schedule[target_day], travel_mode)
                trip["trip"]["day_schedule"] = day_schedule

        # Recalculate budget and summaries if places were changed
        if "remove_place" in parsed or "add_place" in parsed:
            scheduled_activity_count = sum(len(day_places) for day_places in day_schedule.values())
            existing_budget = trip["trip"].get("budget") or {}
            prior_budget = existing_budget.get("total_budget") or existing_budget.get("total") or 0
            trip["trip"]["budget"] = calculate_budget(
                trip["trip"]["travelers"],
                trip["trip"]["days"],
                trip["trip"]["travel_mode"],
                trip["trip"]["hotels"],
                trip["trip"]["places"],
                scheduled_activity_count=scheduled_activity_count,
                total_budget=prior_budget,
            )
            trip["dashboard"] = build_dashboard(trip["trip"])
            trip["trip"]["dashboard"] = trip["dashboard"]
            trip["summary"] = build_summary(trip["trip"])
            trip["trip"]["summary"] = trip["summary"]

        # =================================
        # REGENERATE DAY
        # =================================

        if "regenerate_day" in parsed:

            day_number = parsed[
                "regenerate_day"
            ]

            # --------------------------------
            # Apply requested budget first
            # --------------------------------

            if "budget" in parsed:

                trip["trip"][
                    "budget"
                ][
                    "total_budget"
                ] = parsed["budget"]

            # --------------------------------
            # Regenerate requested day
            # --------------------------------

            trip = regenerate_day(
                trip,
                day_number,
                preferred_interests=parsed.get("preferred_interests", []),
                avoid_categories=parsed.get("avoid_categories", []),
            )
            # Generate explanations for attractions in the regenerated day
            for place in trip["trip"]["day_schedule"].get(str(day_number), []):
                place["explanation"] = explain_attraction(place, trip["trip"])

            # --------------------------------
            # Fit remaining trip to budget
            #
            # The regenerated day is protected.
            # --------------------------------

            if "budget" in parsed:

                trip = fit_trip_to_budget(
                    trip,
                    parsed["budget"],
                    protected_day=day_number,
                )

                # Preserve requested budget
                trip["trip"][
                    "budget"
                ][
                    "total_budget"
                ] = parsed["budget"]

        # =================================
        # SET BUDGET ONLY
        # =================================

        elif "budget" in parsed:

            trip = fit_trip_to_budget(
                trip,
                parsed["budget"],
            )

            trip["trip"][
                "budget"
            ][
                "total_budget"
            ] = parsed["budget"]

        # --------------------------------
        # Recalculate dashboard & summary
        # --------------------------------
        trip["dashboard"] = build_dashboard(trip["trip"])
        trip["trip"]["dashboard"] = trip["dashboard"]
        trip["summary"] = build_summary(trip["trip"])
        trip["trip"]["summary"] = trip["summary"]
        trip["trip_id"] = trip_id
        trip["trip"]["trip_id"] = trip_id

        # --------------------------------
        # Save prompt-based update
        # --------------------------------

        update_saved_trip(
            trip_id,
            trip,
        )

        return trip

    # =================================
    # DIRECT BUDGET UPDATE
    # =================================

    if update.budget is not None:

        trip["trip"][
            "budget"
        ][
            "total_budget"
        ] = update.budget

        trip = fit_trip_to_budget(
            trip,
            update.budget,
        )

        trip["trip"][
            "budget"
        ][
            "total_budget"
        ] = update.budget

    # --------------------------------
    # Recalculate dashboard & summary
    # --------------------------------
    from backend.services.planner.dashboard import build_dashboard
    from backend.services.planner.trip_summary import build_summary
    trip["dashboard"] = build_dashboard(trip["trip"])
    trip["trip"]["dashboard"] = trip["dashboard"]
    trip["summary"] = build_summary(trip["trip"])
    trip["trip"]["summary"] = trip["summary"]
    trip["trip_id"] = trip_id
    trip["trip"]["trip_id"] = trip_id

    # --------------------------------
    # Save direct update
    # --------------------------------

    update_saved_trip(
        trip_id,
        trip,
    )

    return trip


class RealtimeReplanRequest(BaseModel):
    day: int = 1
    completed_attractions: list[str] = []
    remaining_hours: float = 4.0
    current_location: Optional[dict[str, float]] = None
    current_location_name: Optional[str] = None
    remaining_budget: Optional[float] = None


@router.post("/{trip_id}/replan-day")
async def replan_day_endpoint(
    trip_id: str,
    request: RealtimeReplanRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.realtime_replanner import replan_active_day
    updated_inner, audit = replan_active_day(
        trip_data=inner_trip,
        day_number=request.day,
        completed_attraction_names=request.completed_attractions,
        remaining_hours=request.remaining_hours,
        current_location=request.current_location,
        current_location_name=request.current_location_name,
        remaining_budget=request.remaining_budget,
    )

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class AddRouteStopRequest(BaseModel):
    day: int = 1
    route_stop: dict[str, Any]
    allow_repeat: Optional[bool] = False


@router.post("/{trip_id}/add-route-stop")
async def add_route_stop_endpoint(
    trip_id: str,
    request: AddRouteStopRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.route_attractions import insert_route_stop_into_day
    updated_inner, audit = insert_route_stop_into_day(
        trip_data=inner_trip,
        day_number=request.day,
        route_stop=request.route_stop,
        allow_repeat=bool(request.allow_repeat),
    )

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to add route stop"))

    from backend.services.planner.dashboard import build_dashboard
    dash = build_dashboard(updated_inner)
    updated_inner["dashboard"] = dash

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
        raw_trip["dashboard"] = dash
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class SwitchTransportRequest(BaseModel):
    travel_mode: str


@router.post("/{trip_id}/switch-transport")
async def switch_transport_endpoint(
    trip_id: str,
    request: SwitchTransportRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.transport_recommendation_engine import switch_trip_transport
    updated_inner, audit = switch_trip_transport(
        trip_data=inner_trip,
        new_mode=request.travel_mode,
    )

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to switch transport"))

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
        if "dashboard" in raw_trip and "dashboard" in updated_inner:
            raw_trip["dashboard"] = updated_inner["dashboard"]
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class ReallocateBudgetRequest(BaseModel):
    strategy: str = "conservative"
    custom_categories: Optional[dict[str, int]] = None


@router.post("/{trip_id}/reallocate-budget")
async def reallocate_budget_endpoint(
    trip_id: str,
    request: ReallocateBudgetRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.budget_reallocator import apply_budget_reallocation
    updated_inner, audit = apply_budget_reallocation(
        trip_data=inner_trip,
        strategy=request.strategy,
        custom_categories=request.custom_categories,
    )

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to reallocate budget"))

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
        if "dashboard" in updated_inner:
            raw_trip["dashboard"] = updated_inner["dashboard"]
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class GroupVoteRequest(BaseModel):
    traveler_name: str
    attraction_name: str
    vote: str  # 'up', 'neutral', 'down'


@router.post("/{trip_id}/group-vote")
async def group_vote_endpoint(
    trip_id: str,
    request: GroupVoteRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.group_decision_engine import cast_group_vote
    updated_inner, audit = cast_group_vote(
        trip_data=inner_trip,
        traveler_name=request.traveler_name,
        attraction_name=request.attraction_name,
        vote=request.vote,
    )

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to cast vote"))

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


@router.post("/{trip_id}/resolve-group-conflicts")
async def resolve_group_conflicts_endpoint(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.group_decision_engine import resolve_group_conflicts
    updated_inner, audit = resolve_group_conflicts(
        trip_data=inner_trip,
    )

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to resolve conflicts"))

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
        if "dashboard" in updated_inner:
            raw_trip["dashboard"] = updated_inner["dashboard"]
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)
    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class AssistantChatRequest(BaseModel):
    message: str


@router.post("/{trip_id}/assistant-chat")
async def assistant_chat_endpoint(
    trip_id: str,
    request: AssistantChatRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, user_role = verify_trip_access(trip_id, uid, required_role="viewer")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.ai_assistant import answer_trip_question
    result = answer_trip_question(
        trip_data=inner_trip,
        message=request.message,
    )

    mutation = result.get("mutation_action")
    # Only allow mutation to modify the saved trip if user is editor or owner
    if mutation and mutation.get("applied") and mutation.get("updated_trip"):
        if user_role in ("editor", "owner"):
            inner_trip = mutation["updated_trip"]
        else:
            mutation["applied"] = False
            mutation["error"] = "Viewers cannot apply trip mutations"

    # Store message in history if exists (only for editors/owners or keep in-memory for session)
    if user_role in ("editor", "owner"):
        history = inner_trip.get("assistant_history", [])
        history.append({"role": "user", "text": request.message})
        history.append({"role": "assistant", "text": result["reply"]})
        inner_trip["assistant_history"] = history[-20:]  # Keep latest 20

        if "trip" in raw_trip:
            raw_trip["trip"] = inner_trip
            if "dashboard" in inner_trip:
                raw_trip["dashboard"] = inner_trip["dashboard"]
        else:
            raw_trip = inner_trip

        update_saved_trip(trip_id, raw_trip)

    return {
        "success": True,
        "reply": result["reply"],
        "topic": result["topic"],
        "suggested_actions": result["suggested_actions"],
        "trip_highlights": result["trip_highlights"],
        "mutation_action": mutation,
        "trip": inner_trip,
    }


@router.get("/{trip_id}/optimization-score")
async def get_optimization_score_endpoint(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.ai_trip_optimizer import calculate_trip_optimization_score
    score_data = calculate_trip_optimization_score(inner_trip)

    # Cache back into trip
    inner_trip["optimization_score"] = score_data
    if "trip" in raw_trip:
        raw_trip["trip"] = inner_trip
    else:
        raw_trip = inner_trip
    update_saved_trip(trip_id, raw_trip)

    return {
        "success": True,
        "optimization_score": score_data,
    }


@router.post("/{trip_id}/optimize-trip")
async def optimize_trip_endpoint(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    from backend.services.planner.ai_trip_optimizer import optimize_trip_itinerary
    updated_inner, audit = optimize_trip_itinerary(inner_trip)

    if not audit.get("success", False):
        raise HTTPException(status_code=400, detail=audit.get("error", "Failed to optimize trip"))

    if "trip" in raw_trip:
        raw_trip["trip"] = updated_inner
        if "dashboard" in updated_inner:
            raw_trip["dashboard"] = updated_inner["dashboard"]
    else:
        raw_trip = updated_inner

    update_saved_trip(trip_id, raw_trip)

    return {
        "success": True,
        "trip": updated_inner,
        "audit": audit,
    }


class AttractionActionRequest(BaseModel):
    day: str
    attraction_name: str
    action: Literal["remove", "replace"]
    replacement_place: Optional[Dict[str, Any]] = None


@router.get("/{trip_id}/attraction-alternatives")
async def get_attraction_alternatives(
    trip_id: str,
    day: str = Query(..., description="Day number/key to find alternatives for"),
    attraction_name: str = Query(..., description="Name of attraction to replace or remove"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    day_schedule = inner_trip.get("day_schedule", {})

    # Determine destination context and coordinates for this day
    dest_name = inner_trip.get("destination", "Destination")
    dest_lat = None
    dest_lon = None

    # Check multi-destination stops
    destinations = inner_trip.get("destinations", [])
    if destinations:
        try:
            day_num = int(day)
            for stop in destinations:
                if stop.get("start_day", 1) <= day_num <= stop.get("end_day", 1):
                    dest_name = stop.get("name", dest_name)
                    loc = stop.get("location") or {}
                    dest_lat = loc.get("lat")
                    dest_lon = loc.get("lon")
                    break
        except (ValueError, TypeError):
            pass

    if dest_lat is None or dest_lon is None:
        dest_loc = inner_trip.get("destination_location") or {}
        dest_lat = dest_loc.get("lat")
        dest_lon = dest_loc.get("lon")

    # If still not found, check existing places in the day
    if dest_lat is None or dest_lon is None:
        for p in day_schedule.get(str(day), []):
            if p.get("lat") is not None and p.get("lon") is not None:
                dest_lat = p.get("lat")
                dest_lon = p.get("lon")
                break

    # Gather all places already present in the trip schedule
    scheduled_names = set()
    for d_key, places_list in day_schedule.items():
        for p in places_list:
            p_name = p.get("name")
            if p_name:
                scheduled_names.add(normalize_place_name(p_name))

    excluded_names = {
        normalize_place_name(x) for x in inner_trip.get("excluded_places", []) if x
    }
    target_norm = normalize_place_name(attraction_name)
    scheduled_names.add(target_norm)

    alternatives = []
    seen_names = set()

    # 1. First look in inner_trip's candidate places
    for p in inner_trip.get("places", []):
        p_name = p.get("name")
        if not p_name:
            continue
        p_norm = normalize_place_name(p_name)
        if p_norm in scheduled_names or p_norm in excluded_names or p_norm in seen_names:
            continue

        seen_names.add(p_norm)
        category = p.get("category") or "Attraction"
        alternatives.append({
            "name": p_name,
            "category": category,
            "description": p.get("description") or p.get("explanation") or f"Popular {category.lower()} in {dest_name}.",
            "score": p.get("score", 0),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "distance_km": p.get("distance_km", 0),
            "estimated_cost": p.get("estimated_cost", 0),
        })

    # 2. If pool is small and coordinates exist, fetch external places
    if len(alternatives) < 8 and dest_lat is not None and dest_lon is not None:
        try:
            from backend.services.external.place_service import get_places
            external_places = await get_places(float(dest_lat), float(dest_lon))
            for ep in external_places:
                ep_name = ep.get("name")
                if not ep_name:
                    continue
                ep_norm = normalize_place_name(ep_name)
                if ep_norm in scheduled_names or ep_norm in excluded_names or ep_norm in seen_names:
                    continue

                seen_names.add(ep_norm)
                raw_kinds = ep.get("kinds", "")
                cat = raw_kinds.split(",")[0].replace("_", " ").title() if raw_kinds else "Attraction"
                point = ep.get("point") or {}
                alternatives.append({
                    "name": ep_name,
                    "category": cat,
                    "description": f"Verified {cat.lower()} located in {dest_name}.",
                    "score": round(ep.get("rate", 3.5), 1),
                    "lat": point.get("lat", dest_lat),
                    "lon": point.get("lon", dest_lon),
                    "distance_km": round(ep.get("dist", 0) / 1000, 2),
                    "estimated_cost": 0,
                })
                if len(alternatives) >= 15:
                    break
        except Exception as e:
            logger.warning(f"Failed to fetch external place alternatives: {e}")

    # Sort alternatives by score descending
    alternatives.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "success": True,
        "destination": dest_name,
        "day": str(day),
        "attraction_name": attraction_name,
        "alternatives": alternatives,
        "total_available": len(alternatives),
    }


@router.post("/{trip_id}/attraction-action")
async def execute_attraction_action_endpoint(
    trip_id: str,
    request: AttractionActionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="editor")
    raw_trip = trip_record.get("data")
    if not raw_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = raw_trip.get("trip", raw_trip)
    day_schedule = inner_trip.get("day_schedule", {})
    day_key = str(request.day)

    if day_key not in day_schedule:
        raise HTTPException(
            status_code=404,
            detail=f"Day {day_key} not found in trip itinerary",
        )

    day_places = day_schedule[day_key]
    target_norm = normalize_place_name(request.attraction_name)

    # Locate the target attraction in day_places
    match_idx = None
    for idx, p in enumerate(day_places):
        p_name = p.get("name", "")
        if normalize_place_name(p_name) == target_norm:
            match_idx = idx
            break

    if match_idx is None:
        for idx, p in enumerate(day_places):
            p_name = p.get("name", "").lower()
            if target_norm in p_name or p_name in target_norm:
                match_idx = idx
                break

    if match_idx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Attraction '{request.attraction_name}' not found on Day {day_key}",
        )

    travel_mode = inner_trip.get("travel_mode", "car")

    if request.action == "remove":
        removed_place = day_places.pop(match_idx)
        removed_name = removed_place.get("name", request.attraction_name)
        inner_trip.setdefault("excluded_places", []).append(removed_name)
        inner_trip["places"] = [
            p for p in inner_trip.get("places", [])
            if normalize_place_name(p.get("name", "")) != target_norm
        ]
        # Recalculate schedule timings, legs, distances for the affected day
        day_schedule[day_key] = recalculate_day_transit_and_legs(day_places, travel_mode)

    elif request.action == "replace":
        if not request.replacement_place or not request.replacement_place.get("name"):
            raise HTTPException(
                status_code=400,
                detail="A valid replacement_place object with a name is required for replace action.",
            )

        replacement = dict(request.replacement_place)
        rep_name = replacement.get("name", "").strip()
        norm_rep = normalize_place_name(rep_name)

        if not rep_name:
            raise HTTPException(status_code=400, detail="Replacement attraction name cannot be empty.")

        # Ensure replacement is not already scheduled in any day of the itinerary
        for d_k, d_pls in day_schedule.items():
            for p in d_pls:
                if normalize_place_name(p.get("name", "")) == norm_rep:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Attraction '{rep_name}' is already scheduled on Day {d_k}.",
                    )

        removed_place = day_places[match_idx]
        removed_name = removed_place.get("name", request.attraction_name)

        # Attach explanation if missing
        if not replacement.get("explanation"):
            try:
                replacement["explanation"] = explain_attraction(replacement, inner_trip)
            except Exception:
                pass

        # In-place slot replacement to preserve ordering
        day_places[match_idx] = replacement
        inner_trip.setdefault("excluded_places", []).append(removed_name)

        # Update candidate places list
        inner_trip["places"] = [
            p for p in inner_trip.get("places", [])
            if normalize_place_name(p.get("name", "")) != target_norm
        ]
        if not any(normalize_place_name(p.get("name", "")) == norm_rep for p in inner_trip.get("places", [])):
            inner_trip.setdefault("places", []).append(replacement)

        # Recalculate schedule timings, legs, distances for the affected day
        day_schedule[day_key] = recalculate_day_transit_and_legs(day_places, travel_mode)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported action '{request.action}'. Must be 'remove' or 'replace'.",
        )

    # Recalculate overall budget
    from backend.services.planner.budget_tracker import calculate_budget
    scheduled_activity_count = sum(len(pls) for pls in day_schedule.values())
    existing_budget = inner_trip.get("budget") or {}
    prior_budget = existing_budget.get("total_budget") or existing_budget.get("total") or 0
    inner_trip["budget"] = calculate_budget(
        inner_trip.get("travelers", []),
        inner_trip.get("days", len(day_schedule)),
        inner_trip.get("travel_mode", "car"),
        inner_trip.get("hotels", []),
        inner_trip.get("places", []),
        scheduled_activity_count=scheduled_activity_count,
        total_budget=prior_budget,
    )

    # Recalculate dashboard & summary
    from backend.services.planner.dashboard import build_dashboard
    from backend.services.planner.trip_summary import build_summary
    inner_trip["dashboard"] = build_dashboard(inner_trip)
    inner_trip["summary"] = build_summary(inner_trip)

    # Recalculate optimization score
    try:
        from backend.services.planner.ai_trip_optimizer import calculate_trip_optimization_score
        inner_trip["optimization_score"] = calculate_trip_optimization_score(inner_trip)
    except Exception as e:
        logger.warning(f"Could not recalculate optimization score: {e}")

    # Recalculate meals and breaks if present
    if "meals_and_breaks" in inner_trip:
        try:
            from backend.services.planner.meal_and_break_engine import attach_meals_and_breaks_to_itinerary
            inner_trip["meals_and_breaks"] = attach_meals_and_breaks_to_itinerary(
                day_schedule=inner_trip["day_schedule"],
                travelers=inner_trip.get("travelers", []),
                destination=inner_trip.get("destination", ""),
            )
        except Exception as e:
            logger.warning(f"Could not recalculate meals and breaks: {e}")

    # Prepare and persist updated trip
    if "trip" in raw_trip:
        raw_trip["trip"] = inner_trip
        if "dashboard" in inner_trip:
            raw_trip["dashboard"] = inner_trip["dashboard"]
        if "summary" in inner_trip:
            raw_trip["summary"] = inner_trip["summary"]
    else:
        raw_trip = inner_trip

    try:
        update_saved_trip(trip_id, raw_trip)
    except Exception as e:
        logger.error(f"Failed to persist trip updates for {trip_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist itinerary updates: {str(e)}",
        )

    return {
        "success": True,
        "trip": inner_trip,
        "message": f"Attraction '{request.attraction_name}' successfully {'removed' if request.action == 'remove' else 'replaced'} on Day {day_key}.",
    }

