"""
Smart Waiter API – the backend for the React UI (replaces main.py / Streamlit as the server side).
The React app (frontend/) sends requests here, and SearchEngine runs against ChromaDB.

Run:
    venv/Scripts/python.exe -m uvicorn api:app --reload --port 8000
"""
import logging
import sys
from contextlib import asynccontextmanager

# Logs include Hebrew dish names; a Windows console (cp1252) crashes on them, so force UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.search_engine import SearchEngine

CSV_PATH = "japanika_menu_enriched_complete.csv"
engine: SearchEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the engine once when the server starts (replaces @st.cache_resource)
    global engine
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    engine = SearchEngine()
    engine.ensure_index(CSV_PATH)  # rebuilds only if the CSV or the index format changed
    yield


app = FastAPI(title="Japanika Smart Waiter API", lifespan=lifespan)

# In development React goes through the Vite proxy, but CORS is kept
# in case the API is called directly from localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = ""
    # {"is_vegan": True} = "with", {"contains_gluten": False} = "without"; missing key = "any"
    filters: dict[str, bool] = {}
    # How many results to return; the UI's "show more" button asks for 10 more each time
    limit: int = Field(10, ge=1, le=100)


@app.get("/api/health")
def health():
    return {"status": "ok", "items": engine.collection.count()}


@app.post("/api/search")
def search(req: SearchRequest):
    # Returns {"results": [...], "total": N, "understood": {"text": ..., "filters": {...}}}
    return engine.search(req.query, active_buttons=req.filters, n_results=req.limit)
