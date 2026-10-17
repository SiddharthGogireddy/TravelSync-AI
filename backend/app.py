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
from backend.routes.location import router as location_router
from backend.routes.currency import router as currency_router
from backend.routes.weather import router as weather_router
from backend.routes.chat import router as chat_router
from backend.routes.activity import router as activity_router
from backend.routes.memory import router as memory_router
from backend.routes.invitation import router as invitation_router
from backend.routes.auth import router as auth_router
from backend.routes.migration import router as migration_router
from backend.routes.update_trip import (
    router as update_trip_router,
)
from backend.services.trip_editor.llm_interpreter import interpret_trip_prompt
load_dotenv()
from backend.services.auth.jwt_service import validate_jwt_secrets_config, is_auth_dev_mode
from backend.services.auth.cors_config import parse_cors_origins
from backend.routes.explanation import router as explanation_router
from backend.services.error.exception_handlers import register_exception_handlers
from backend.services.security.rate_limiter import RateLimiterMiddleware

from contextlib import asynccontextmanager

# Validate JWT secrets and CORS configuration at startup
validate_jwt_secrets_config()
cors_origins = parse_cors_origins()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_jwt_secrets_config()
    yield


app = FastAPI(title="TravelSync AI", lifespan=lifespan)
register_exception_handlers(app)

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
app.include_router(chat_router)
app.include_router(activity_router)
app.include_router(memory_router)
app.include_router(location_router)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": "TravelSync AI"}


app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
if is_auth_dev_mode():
    @app.get("/test-llm", tags=["Diagnostics"])
    async def test_llm():
        return interpret_trip_prompt(
            "Regenerate Day 2 and keep the budget under ₹30,000"
        )