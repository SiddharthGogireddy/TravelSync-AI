from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from backend.api.ai import router as ai_router

app = FastAPI()

app.include_router(ai_router)