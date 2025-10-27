import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from skyfield.api import EarthSatellite, load

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "satellite_db",
    "user": "postgres",
    "password": "gshekhar81461",
    "host": "localhost",
    "port": "5432"
}

# --- FastAPI Application ---
app = FastAPI(
    title="Satellite Digital Twin API",
    description="API for tracking satellite positions.",
    version="1.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database connection error: {error}")
        return None

def calculate_satellite_position(line1: str, line2: str):
    """
    Calculates current satellite position using Skyfield.
    Returns (latitude, longitude, altitude) in degrees and km.
    """
    try:
        ts = load.timescale()
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


@app.get("/api/v1/satellites")
def get_satellite_positions():
    """
    Fetches the latest TLE for each satellite, calculates its current
    position, and returns a list of satellite data.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    satellites_data = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    s.name, 
                    s.norad_cat_id, 
                    t.line1, 
                    t.line2
                FROM 
                    satellites s
                JOIN (
                    SELECT 
                        satellite_id, 
                        line1, 
                        line2,
                        ROW_NUMBER() OVER(PARTITION BY satellite_id ORDER BY epoch DESC) AS rn
                    FROM 
                        tles
                ) t ON s.id = t.satellite_id
                WHERE t.rn = 1;
            """)

            satellites = cur.fetchall()
            print(f"Fetched {len(satellites)} satellites from database.")

            for sat in satellites:
                pos = calculate_satellite_position(sat['line1'], sat['line2'])
                if pos:
                    lat, lon, alt = pos
                    satellites_data.append({
                        "name": sat['name'],
                        "norad_id": sat['norad_cat_id'],
                        "latitude": lat,
                        "longitude": lon,
                        "altitude": alt
                    })
                else:
                    print(f"Skipping {sat['name']} — position calculation failed.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"API Error: {error}")
        raise HTTPException(status_code=500, detail="Error processing satellite data")

    finally:
        if conn:
            conn.close()

    return {"satellites": satellites_data}

# Run with:
# uvicorn main:app --reload
