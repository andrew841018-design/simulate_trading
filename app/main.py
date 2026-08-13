"build api"
from fastapi import FastAPI
app = FastAPI()
@app.get("/live")
def live_endpoint():
    return {"status": "Live endpoint is working!"}
