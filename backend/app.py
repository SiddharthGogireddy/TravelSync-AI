from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.services.auth.authorization import set_current_request, reset_current_request
from backend.routes.expense import router as expense_router
from backend.api.ai import router as ai_router
from backend.routes.planner import router as planner_router
from backend.routes.trip import router as trip_router
from backend.routes.template import router as template_router
from backend.routes.pdf import router as pdf_router
from backend.routes.place import router as place_router
from backend.routes.currency import router as currency_router
from backend.routes.weather import router as weather_router
from backend.routes.invitation import router as invitation_router
from backend.routes.auth import router as auth_router
from backend.routes.migration import router as migration_router
from backend.routes.update_trip import (
    router as update_trip_router,
)
from backend.services.trip_editor.llm_interpreter import interpret_trip_prompt
load_dotenv()
from backend.routes.explanation import router as explanation_router
app = FastAPI(title="TravelSync AI")

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    token = set_current_request(request)
    try:
        response = await call_next(request)
        return response
    finally:
        reset_current_request(token)


app.include_router(auth_router)
app.include_router(migration_router)
app.include_router(planner_router)
app.include_router(trip_router)
app.include_router(invitation_router)
app.include_router(template_router)
app.include_router(ai_router)
app.include_router(expense_router)
app.include_router(pdf_router)
app.include_router(place_router)
app.include_router(currency_router)
app.include_router(weather_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    update_trip_router
)
app.include_router(
    explanation_router,
    prefix="/explanation",
    tags=["Explanation"],
)
@app.get("/test-llm")
async def test_llm():
    return interpret_trip_prompt(
        "Regenerate Day 2 and keep the budget under ₹30,000"
    )