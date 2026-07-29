from fastapi import FastAPI
from routes.trip import router as trip_router

app = FastAPI(title="TravelSync AI")

app.include_router(trip_router)

@app.get("/")
def root():
    return {"message": "TravelSync AI Backend Running"}