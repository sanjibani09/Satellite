# analysis/analysis_api_free.py
"""
FREE Analysis API using Microsoft Planetary Computer
No billing required - 100% open source and free!

Replace your analysis_api.py with this file
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import asyncio
import json
from datetime import datetime

# Import the free planetary computer client
try:
    from planetary_computer_ingest import PlanetaryComputerClient
except ImportError:
    from .planetary_computer_ingest import PlanetaryComputerClient

app = FastAPI(title="GeoGPT Analysis Service (FREE)", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the FREE client
print("🌍 Initializing Microsoft Planetary Computer (FREE)")
pc_client = PlanetaryComputerClient()

# ===== Request/Response Models =====

class AnalysisTypeEnum(str, Enum):
    VEGETATION_HEALTH = "vegetation_health"
    FLOOD_DETECTION = "flood_detection"
    WATER_DETECTION = "water_detection"
    URBAN_GROWTH = "urban_growth"

class AnalysisRequest(BaseModel):
    aoi_geojson: Dict = Field(..., description="Area of Interest as GeoJSON")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    analysis_types: List[AnalysisTypeEnum] = Field(
        default=["vegetation_health"],
        description="Types of analysis to perform"
    )
    max_cloud_cover: float = Field(default=30, ge=0, le=100)

class ChangeDetectionRequest(BaseModel):
    aoi_geojson: Dict
    before_start: str
    before_end: str
    after_start: str
    after_end: str
    max_cloud_cover: float = 30

# ===== API Endpoints =====

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GeoGPT Analysis Service (FREE)",
        "data_source": "Microsoft Planetary Computer",
        "billing": "Not required - 100% free!",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/analyze", response_model=Dict)
async def analyze_imagery(request: AnalysisRequest):
    """
    Perform ML analysis on satellite imagery (FREE - No billing!)
    """
    try:
        print(f"\n📡 Analysis request received")
        print(f"   Date range: {request.start_date} to {request.end_date}")
        print(f"   Analysis types: {request.analysis_types}")
        
        # Convert enum to strings
        analysis_types = [at.value for at in request.analysis_types]
        
        # Run analysis using FREE Planetary Computer
        results = pc_client.analyze_region(
            aoi_geojson=request.aoi_geojson,
            start_date=request.start_date,
            end_date=request.end_date,
            analysis_types=analysis_types,
            max_cloud_cover=request.max_cloud_cover
        )
        
        if results["status"] == "error":
            raise HTTPException(status_code=404, detail=results["message"])
        
        # Add metadata
        results["aoi"] = request.aoi_geojson
        results["time_period"] = f"{request.start_date} to {request.end_date}"
        results["data_source"] = "Microsoft Planetary Computer (Sentinel-2)"
        results["timestamp"] = datetime.utcnow().isoformat()
        
        return results
    
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/v1/change-detection", response_model=Dict)
async def detect_changes(request: ChangeDetectionRequest):
    """
    Detect changes between two time periods (FREE)
    """
    try:
        print(f"\n🔄 Change detection request")
        print(f"   Before: {request.before_start} to {request.before_end}")
        print(f"   After: {request.after_start} to {request.after_end}")
        
        # Analyze both periods
        before_results = pc_client.analyze_region(
            aoi_geojson=request.aoi_geojson,
            start_date=request.before_start,
            end_date=request.before_end,
            analysis_types=["vegetation_health"],
            max_cloud_cover=request.max_cloud_cover
        )
        
        after_results = pc_client.analyze_region(
            aoi_geojson=request.aoi_geojson,
            start_date=request.after_start,
            end_date=request.after_end,
            analysis_types=["vegetation_health"],
            max_cloud_cover=request.max_cloud_cover
        )
        
        if before_results["status"] == "error" or after_results["status"] == "error":
            raise HTTPException(status_code=404, detail="Could not find imagery for one or both periods")
        
        # Calculate changes
        before_ndvi = before_results["analyses"]["vegetation_health"]["statistics"]["mean_ndvi"]
        after_ndvi = after_results["analyses"]["vegetation_health"]["statistics"]["mean_ndvi"]
        
        ndvi_change = after_ndvi - before_ndvi
        percent_change = (ndvi_change / before_ndvi * 100) if before_ndvi != 0 else 0
        
        # Interpret change
        if ndvi_change < -0.1:
            interpretation = f"Significant vegetation loss detected ({percent_change:.1f}% decrease). Possible deforestation, drought, or urban expansion."
        elif ndvi_change > 0.1:
            interpretation = f"Vegetation increase detected ({percent_change:.1f}% increase). Possible reforestation, agricultural growth, or seasonal changes."
        else:
            interpretation = "Minimal change in vegetation cover. Conditions remain relatively stable."
        
        return {
            "status": "success",
            "before_period": {
                "date_range": f"{request.before_start} to {request.before_end}",
                "image_date": before_results["image_date"],
                "mean_ndvi": before_ndvi
            },
            "after_period": {
                "date_range": f"{request.after_start} to {request.after_end}",
                "image_date": after_results["image_date"],
                "mean_ndvi": after_ndvi
            },
            "change_detection": {
                "ndvi_change": ndvi_change,
                "percent_change": percent_change,
                "interpretation": interpretation
            },
            "data_source": "Microsoft Planetary Computer (Sentinel-2)",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Change detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Change detection failed: {str(e)}")

@app.get("/api/v1/available-dates")
async def get_available_dates(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    max_cloud_cover: float = 30
):
    """
    Check what imagery dates are available for an AOI
    """
    try:
        from datetime import timedelta
        
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat]
            ]]
        }
        
        # Search last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        items = pc_client.search_sentinel2(
            aoi_geojson=aoi,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            max_cloud_cover=max_cloud_cover
        )
        
        dates = [
            {
                "date": item.datetime.date().isoformat(),
                "cloud_cover": item.properties.get("eo:cloud_cover", "N/A")
            }
            for item in items
        ]
        
        return {
            "status": "success",
            "aoi": aoi,
            "available_dates": dates,
            "count": len(dates),
            "data_source": "Microsoft Planetary Computer"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if _name_ == "_main_":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Starting FREE Analysis API")
    print("   Using: Microsoft Planetary Computer")
    print("   Billing: NOT REQUIRED - 100% FREE!")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)