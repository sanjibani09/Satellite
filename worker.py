import asyncio
import asyncpg # New async DB driver
import redis
import json
from datetime import datetime
from skyfield.api import EarthSatellite, load

# --- Database Configuration (Using your updated config) ---
DB_CONFIG = {
    "database": "satellite_db",
    "user": "postgres",
    "password": "sanjibanipaul",
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

# --- MODIFIED Calculation Function (for Step 2.3) ---
def calculate_satellite_position(line1: str, line2: str):
    """
    Calculates current satellite position using Skyfield.
    Returns a dictionary containing:
    - eci_pos: (x, y, z) tuple in ECI coordinates (km)
    - geo_pos: (lat, lon, alt) tuple in degrees and km
    """
    try:
        t = ts.now()  # current UTC time
        satellite = EarthSatellite(line1, line2)
        
        # 1. Get the ECI position vector
        eci_position_vector = satellite.at(t).position.km
        
        # 2. Get the subpoint (geographic)
        subpoint = satellite.at(t).subpoint()

        # 3. Package and return
        return {
            "eci_pos": tuple(eci_position_vector), # (x, y, z)
            "geo_pos": (
                subpoint.latitude.degrees,
                subpoint.longitude.degrees,
                subpoint.elevation.km
            )
        }

    except Exception as e:
        print(f"Error in calculation: {e}")
        return None


async def fetch_and_calculate(pool):
    """
    The main logic function for the worker.
    """
    print(f"[{datetime.now()}] Worker cycle starting: Fetching TLEs...")
    
    satellites_data = [] # For Redis cache
    
    try:
        async with pool.acquire() as conn:
            # *** MODIFIED QUERY: Added s.id ***
            satellites = await conn.fetch("""
                SELECT 
                    s.id as satellite_db_id, 
                    s.name, 
                    s.norad_cat_id, 
                    t.line1, 
                    t.line2
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
        
        calculation_tasks = []
        for sat in satellites:
            task = asyncio.to_thread(
                calculate_satellite_position, sat['line1'], sat['line2']
            )
            calculation_tasks.append((sat, task))

        # --- Lists for this cycle ---
        all_eci_positions = []    # For Collision Analysis
        all_satellite_info = []   # For Collision Analysis
        
        # --- *** NEW: List for executemany arguments *** ---
        postgis_update_args = [] 

        
        # --- Calculation Loop (No DB connection needed here) ---
        for sat, task in calculation_tasks:
            pos_data = await task # Get the result from the thread
            
            if pos_data:
                eci_pos = pos_data["eci_pos"]
                lat, lon, alt = pos_data["geo_pos"]
                
                # 1. Prepare data for the API Cache (same as before)
                satellites_data.append({
                    "name": sat['name'],
                    "norad_id": sat['norad_cat_id'],
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt
                })
                
                # 2. Store data for collision analysis
                all_eci_positions.append(eci_pos)
                all_satellite_info.append({
                    "id": sat['satellite_db_id'],
                    "name": sat['name'],
                    "norad_id": sat['norad_cat_id']
                })

                # 3. --- *** NEW: Append arguments for PostGIS update *** ---
                # Arguments must be in order: $1 (lon), $2 (lat), $3 (id)
                postgis_update_args.append(
                    (lon, lat, sat['satellite_db_id'])
                )
        
        # --- *** NEW: Run all DB updates in one batch *** ---
        if postgis_update_args:
            async with pool.acquire() as conn:
                try:
                    await conn.executemany(
                        """
                        UPDATE satellites 
                        SET geopoint = ST_SetSRID(ST_MakePoint($1, $2), 4326)
                        WHERE id = $3
                        """,
                        postgis_update_args
                    )
                    print(f"PostGIS OK: Updated geopoints for {len(postgis_update_args)} satellites.")
                except Exception as e:
                    print(f"WORKER Error during PostGIS update: {e}")

        
        # --- Collision Analysis Section (Placeholder) ---
        if all_eci_positions:
            print(f"Collision Check: Built position list for {len(all_eci_positions)} satellites.")
            # We will add the KDTree logic here in the next step
            pass 
            
        print(f"Calculation OK: Processed {len(satellites_data)} satellites.")

        # --- Write final result to Redis (same as before) ---
        if redis_client and satellites_data:
            json_data = json.dumps({"satellites": satellites_data})
            redis_client.set(CACHE_KEY, json_data, ex=CACHE_TTL_SECONDS)
            print("Cache Write OK: Updated satellite positions in Redis.")

    except (Exception, asyncpg.PostgresError) as error:
        # This will catch errors from the initial .fetch()
        print(f"WORKER Error in main cycle: {error}")

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

