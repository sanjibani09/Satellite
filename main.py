from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
import json

# --- Constants ---
CACHE_KEY = "satellite_positions_v2"  # must match worker.py key

app = FastAPI()

# --- Redis Connection ---
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("API: Connected to Redis successfully.")
except redis.exceptions.ConnectionError as e:
    print(f"API Error: Could not connect to Redis: {e}")
    redis_client = None


# --- Allow all CORS (so frontend can connect) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Route ---
@app.get("/api/v1/satellites")
async def get_satellite_positions_cached():
    """Returns latest cached satellite positions from Redis."""
    if not redis_client:
        print("API Error: Redis not connected")
        return {"error": "Redis not connected"}

    try:
        data = redis_client.get(CACHE_KEY)
        if not data:
            print("API Error: No cached data found in Redis")
            return {"error": "No cached data found"}

        # Parse and return JSON from Redis
        return json.loads(data)

    except Exception as e:
        print(f"API Error: {e}")
        return {"error": str(e)}