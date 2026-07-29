from fastapi import FastAPI
from routes.trip import router as trip_router
from routes.location import router as location_router
from routes.route import router as route_router

app = FastAPI(title="TravelSync AI")
app.include_router(route_router)
app.include_router(location_router)
app.include_router(trip_router)

@app.get("/")
def root():
    return {"message": "TravelSync AI Backend Running"}