from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.routes.expense import router as expense_router
from backend.api.ai import router as ai_router
from backend.routes.planner import router as planner_router
from backend.routes.trip import router as trip_router
from backend.routes.pdf import router as pdf_router
from backend.routes.update_trip import (
    router as update_trip_router,
)

load_dotenv()

app = FastAPI(title="TravelSync AI")

app.include_router(planner_router)
app.include_router(trip_router)
app.include_router(ai_router)
app.include_router(expense_router)
app.include_router(pdf_router)
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