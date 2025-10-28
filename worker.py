import asyncio
import asyncpg # New async DB driver
import redis
import json
from datetime import datetime
from skyfield.api import EarthSatellite, load

# --- Database Configuration (same as yours) ---
DB_CONFIG = {
    "database": "satellite_db",
    "user": "postgres",
    "password": "gshekhar81461",
    "host": "localhost",
    "port": "5432"
}

# --- Cache Configuration ---
CACHE_KEY = "satellite_positions_v2"
CACHE_TTL_SECONDS = 60 # Align with our 1-minute refresh goal
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("WORKER: Successfully connected to Redis cache.")
except redis.exceptions.ConnectionError as e:
    print(f"WORKER Error: Could not connect to Redis: {e}")
    redis_client = None

# --- Skyfield Loader ---
ts = load.timescale()

# --- Your Calculation Function (unchanged) ---
# This is synchronous and CPU-bound, which is PERFECT
# for running in a separate thread via asyncio.to_thread
def calculate_satellite_position(line1: str, line2: str):
    """
    Calculates current satellite position using Skyfield.
    Returns (latitude, longitude, altitude) in degrees and km.
    """
    try:
        t = ts.now()  # current UTC time
        satellite = EarthSatellite(line1, line2)
        subpoint = satellite.at(t).subpoint()

        lat = subpoint.latitude.degrees
        lon = subpoint.longitude.degrees
        alt = subpoint.elevation.km

        return lat, lon, alt

    except Exception as e:
        print(f"Error in calculation: {e}")
        return None

async def fetch_and_calculate(pool):
    """
    The main logic function for the worker.
    """
    print(f"[{datetime.now()}] Worker cycle starting: Fetching TLEs...")
    
    satellites_data = []
    
    try:
        async with pool.acquire() as conn:
            # Use your exact SQL query
            satellites = await conn.fetch("""
                SELECT 
                    s.name, s.norad_cat_id, t.line1, t.line2
                FROM 
                    satellites s
                JOIN (
                    SELECT 
                        satellite_id, line1, line2,
                        ROW_NUMBER() OVER(PARTITION BY satellite_id ORDER BY epoch DESC) AS rn
                    FROM tles
                ) t ON s.id = t.satellite_id
                WHERE t.rn = 1;
            """)
        
        print(f"DB Fetch OK: Found {len(satellites)} satellites. Starting calculations...")
        
        # --- Run CPU-Bound Calculations in a Thread Pool ---
        # We prepare all tasks first
        calculation_tasks = []
        for sat in satellites:
            # asyncio.to_thread runs our sync function in a separate thread
            # so it doesn't block the main async loop.
            task = asyncio.to_thread(
                calculate_satellite_position, sat['line1'], sat['line2']
            )
            calculation_tasks.append((sat, task))

        # Now we run them all concurrently
        for sat, task in calculation_tasks:
            pos = await task # Get the result from the thread
            if pos:
                lat, lon, alt = pos
                satellites_data.append({
                    "name": sat['name'],
                    "norad_id": sat['norad_cat_id'],
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt
                })
        
        print(f"Calculation OK: Processed {len(satellites_data)} satellites.")

        # --- Write final result to Redis ---
        if redis_client and satellites_data:
            json_data = json.dumps({"satellites": satellites_data})
            redis_client.set(CACHE_KEY, json_data, ex=CACHE_TTL_SECONDS)
            print("Cache Write OK: Updated satellite positions in Redis.")

    except (Exception, asyncpg.PostgresError) as error:
        print(f"WORKER Error: {error}")

async def main():
    """
    Main worker loop. Connects to DB and runs the cycle.
    """
    pool = None
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        print("WORKER: Database pool created.")
    except Exception as e:
        print(f"WORKER Error: Could not create DB pool: {e}")
        return

    if not redis_client:
        print("WORKER Error: No Redis connection. Exiting.")
        return

    # --- Main Loop ---
    while True:
        await fetch_and_calculate(pool)
        print(f"Cycle complete. Sleeping for {CACHE_TTL_SECONDS} seconds...")
        await asyncio.sleep(CACHE_TTL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())