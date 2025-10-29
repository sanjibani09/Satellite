# ingestion/sample_run.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ingestion Service (robust)")

# CORS - allow all origins for dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    aoi_geojson: dict
    start_date: str
    end_date: str
    out_prefix: str = "demo"

def _load_modules():
    """
    Try importing as a package (ingestion.*). If that fails,
    fall back to top-level module imports (when cwd=ingestion/).
    Returns tuple: (gee_ingest_module, indexer_module)
    """
    try:
        # Preferred when run from repo root:
        from ingestion import gee_ingest as gee_ingest_mod
        from ingestion import indexer as indexer_mod
    except Exception:
        # Fallback when CWD is ingestion/ and running uvicorn sample_run:app
        try:
            import gee_ingest as gee_ingest_mod
            import indexer as indexer_mod
        except Exception as e:
            # Re-raise with helpful message
            raise ImportError(
                "Could not import gee_ingest/indexer. Make sure ingestion/ has __init__.py "
                "and you are running uvicorn from repo root (python -m uvicorn ingestion.sample_run:app) "
                "or from inside ingestion with python -m uvicorn sample_run:app. Original error: "
                f"{e}"
            )
    return gee_ingest_mod, indexer_mod

@app.post("/ingest")
def ingest(req: IngestRequest):
    gee_mod, _ = _load_modules()
    # mosaic_and_export should handle its own EE initialization (ee.Authenticate/ee.Initialize)
    meta = gee_mod.mosaic_and_export(req.aoi_geojson, req.start_date, req.end_date, out_prefix=req.out_prefix)
    return {"status": "ok", "meta": meta}

@app.get("/index")
def index():
    _, indexer_mod = _load_modules()
    return indexer_mod.list_records()

if __name__ == "__main__":
    # If you run this file directly: python ingestion/sample_run.py
    # it will start a uvicorn server (useful for quick local runs).
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
