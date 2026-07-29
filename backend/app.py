from fastapi import FastAPI

app = FastAPI(title="TravelSync AI")

@app.get("/")
def root():
    return {"message": "TravelSync AI Backend Running"}