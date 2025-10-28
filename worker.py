import asyncio
import asyncpg
import redis
import json
from datetime import datetime, timedelta, timezone
from skyfield.api import EarthSatellite, load

# --- Global Constants ---
PREDICT_SECONDS = 90 * 60        # 90 minutes ahead
SAMPLE_INTERVAL = 30             # seconds between samples
CACHE_KEY = "satellite_positions_v2"
CACHE_TTL_SECONDS = 60           # refresh every minute

# --- Database Configuration ---
DB_CONFIG = {
    "database": "satellite_db",
    "user": "postgres",
    "password": "sanjibanipaul",   # <-- update if needed
    "host": "localhost",
    "port": "5432"
}

# --- Redis Configuration ---
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("WORKER: Successfully connected to Redis cache.")
except redis.exceptions.ConnectionError as e:
    print(f"WORKER Error: Could not connect to Redis: {e}")
    redis_client = None

# --- Skyfield Loader ---
ts = load.timescale()

# ==============================================================
#  Satellite Position + Orbit Prediction Logic
# ==============================================================

def calculate_satellite_position(line1: str, line2: str):
    """
    Calculates current satellite position.
    Returns dict with ECI (x, y, z) km and geodetic lat/lon/alt.
    """
    try:
        t = ts.now()
        sat = EarthSatellite(line1, line2)

        # Earth-Centered Inertial coordinates
        eci = sat.at(t).position.km

        # Geographic subpoint
        sub = sat.at(t).subpoint()
        return {
            "eci_pos": tuple(eci),
            "geo_pos": (
                sub.latitude.degrees,
                sub.longitude.degrees,
                sub.elevation.km
            )
        }
    except Exception as e:
        print(f"Error calculating position: {e}")
        return None


def compute_future_samples(line1: str, line2: str, predict_seconds=PREDICT_SECONDS, sample_interval=SAMPLE_INTERVAL):
    """
    Predicts future orbit samples (lat/lon/alt_km) over next N seconds.
    """
    samples = []
    now_dt_utc = datetime.now(timezone.utc)
    n = int(predict_seconds // sample_interval) + 1
    sat = EarthSatellite(line1, line2)

    for i in range(n):
        t_dt = now_dt_utc + timedelta(seconds=i * sample_interval)
        t_sf = ts.utc(
            t_dt.year, t_dt.month, t_dt.day,
            t_dt.hour, t_dt.minute, t_dt.second + t_dt.microsecond / 1e6
        )
        sub = sat.at(t_sf).subpoint()
        samples.append({
            "t": t_dt.isoformat(),
            "lat": sub.latitude.degrees,
            "lon": sub.longitude.degrees,
            "alt_km": sub.elevation.km
        })
    return samples

# ==============================================================
#  Async Worker Logic
# ==============================================================

async def fetch_and_calculate(pool):
    """
    Fetch latest TLEs, compute positions + predictions,
    update PostGIS, cache results in Redis.
    """
    print(f"[{datetime.now()}] Worker cycle starting: Fetching TLEs...")
    satellites_data = []
    postgis_update_args = []

    try:
        async with pool.acquire() as conn:
            satellites = await conn.fetch("""
                SELECT 
                    s.id as satellite_db_id, 
                    s.name, 
                    s.norad_cat_id, 
                    t.line1, 
                    t.line2
                FROM satellites s
                JOIN (
                    SELECT 
                        satellite_id, line1, line2,
                        ROW_NUMBER() OVER(PARTITION BY satellite_id ORDER BY epoch DESC) AS rn
                    FROM tles
                ) t ON s.id = t.satellite_id
                WHERE t.rn = 1;
            """)

        print(f"DB Fetch OK: Found {len(satellites)} satellites.")

        # --- Concurrently compute positions ---
        calculation_tasks = []
        for sat in satellites:
            task = asyncio.to_thread(calculate_satellite_position, sat['line1'], sat['line2'])
            calculation_tasks.append((sat, task))

        for sat, task in calculation_tasks:
            pos_data = await task
            if not pos_data:
                continue

            eci = pos_data["eci_pos"]
            lat, lon, alt = pos_data["geo_pos"]

            # Predict orbit samples
            try:
                samples = compute_future_samples(sat['line1'], sat['line2'])
            except Exception as e:
                print(f"Prediction error for {sat['name']}: {e}")
                samples = []

            satellites_data.append({
                "id": sat['satellite_db_id'],
                "name": sat['name'],
                "norad_id": sat['norad_cat_id'],
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "eci": eci,
                "samples": samples
            })

            # PostGIS update
            postgis_update_args.append((lon, lat, sat['satellite_db_id']))

        # --- Batch update PostGIS geopoints ---
        if postgis_update_args:
            async with pool.acquire() as conn:
                try:
                    await conn.executemany("""
                        UPDATE satellites 
                        SET geopoint = ST_SetSRID(ST_MakePoint($1, $2), 4326)
                        WHERE id = $3
                    """, postgis_update_args)
                    print(f"PostGIS OK: Updated {len(postgis_update_args)} satellites.")
                except Exception as e:
                    print(f"WORKER Error updating PostGIS: {e}")

        # --- Cache results in Redis ---
        if redis_client and satellites_data:
            json_data = json.dumps({"satellites": satellites_data})
            redis_client.set(CACHE_KEY, json_data, ex=CACHE_TTL_SECONDS)
            print("Cache Write OK: Updated satellite positions in Redis.")

        print(f"Cycle complete. Processed {len(satellites_data)} satellites.")

    except (Exception, asyncpg.PostgresError) as error:
        print(f"WORKER Error: {error}")


async def main():
    """
    Initialize connection pool, then run worker cycles continuously.
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

    while True:
        await fetch_and_calculate(pool)
        await asyncio.sleep(CACHE_TTL_SECONDS)

# --- Entry Point ---
if __name__ == "__main__":
    asyncio.run(main())