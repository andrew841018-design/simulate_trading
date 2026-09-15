"build api"
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers import accounts, orders

app = FastAPI()
app.include_router(accounts.router, prefix="/v1/accounts")
app.include_router(orders.router, prefix="/v1/orders")
main_page_path=Path(__file__).resolve().parent/"static"/"index.html"

@app.get("/live")
def live_endpoint():
    return {"status": "Live endpoint is working!"}
@app.get('/')
def main_page():
    return FileResponse(main_page_path)
