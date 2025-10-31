# analysis/analysis_api_with_llm.py
"""
Enhanced Analysis API with Llama LLM Integration
Adds natural language query support and intelligent explanations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import existing components
try:
    from planetary_computer_ingest import PlanetaryComputerClient
    from llm_interface import GeoGPTLLM, GeoGPTAssistant
    print("✅ Imported analysis components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

app = FastAPI(
    title="GeoGPT Analysis Service with LLM",
    version="3.0",
    description="Satellite imagery analysis powered by AI and Llama"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
print("🌍 Initializing Microsoft Planetary Computer (FREE)...")
pc_client = PlanetaryComputerClient()

print("🦙 Initializing Llama LLM...")
try:
    llm_assistant = GeoGPTAssistant(GeoGPTLLM(model="llama3.1:8b"))
    LLM_ENABLED = True
    print("✅ Llama LLM ready!")
except Exception as e:
    print(f"⚠️ Llama not available: {e}")
    print("   API will work but without LLM explanations")
    llm_assistant = None
    LLM_ENABLED = False

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
    include_llm_explanation: bool = Field(
        default=True,
        description="Generate natural language explanation using LLM"
    )

class ChangeDetectionRequest(BaseModel):
    aoi_geojson: Dict
    before_start: str
    before_end: str
    after_start: str
    after_end: str
    max_cloud_cover: float = 30
    include_llm_explanation: bool = True

class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language query")
    context: Optional[Dict] = Field(
        None,
        description="Optional analysis results for context"
    )

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language geospatial query")

# ===== API Endpoints =====

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GeoGPT Analysis Service",
        "version": "3.0 (with LLM)",
        "data_source": "Microsoft Planetary Computer",
        "llm_model": "Llama 3.1 (8B)" if LLM_ENABLED else "Disabled",
        "billing": "Not required - 100% free!",
        "endpoints": {
            "health": "/api/v1/health",
            "analyze": "/api/v1/analyze",
            "change_detection": "/api/v1/change-detection",
            "chat": "/api/v1/chat",
            "query": "/api/v1/query",
            "docs": "/docs"
        }
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GeoGPT Analysis Service",
        "data_source": "Microsoft Planetary Computer",
        "llm_enabled": LLM_ENABLED,
        "llm_model": "llama3.1:8b" if LLM_ENABLED else None,
        "billing": "Not required - 100% free!",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/analyze")
async def analyze_imagery(request: AnalysisRequest):
    """
    Perform ML analysis on satellite imagery with LLM explanations
    """
    try:
        print(f"\n📡 Analysis request received")
        print(f"   Date range: {request.start_date} to {request.end_date}")
        print(f"   Analysis types: {request.analysis_types}")
        print(f"   LLM explanation: {request.include_llm_explanation}")
        
        # Convert enum to strings
        analysis_types = [at.value for at in request.analysis_types]
        
        # Run satellite analysis
        results = pc_client.analyze_region(
            aoi_geojson=request.aoi_geojson,
            start_date=request.start_date,
            end_date=request.end_date,
            analysis_types=analysis_types,
            max_cloud_cover=request.max_cloud_cover
        )
        
        if results["status"] == "error":
            raise HTTPException(
                status_code=404,
                detail={
                    "message": results["message"],
                    "suggestions": results.get("suggestions", [])
                }
            )
        
        # Add basic metadata
        results["aoi"] = request.aoi_geojson
        results["time_period"] = f"{request.start_date} to {request.end_date}"
        results["data_source"] = "Microsoft Planetary Computer (Sentinel-2) - FREE"
        results["timestamp"] = datetime.utcnow().isoformat()
        
        # Generate LLM explanations if enabled
        if request.include_llm_explanation and LLM_ENABLED:
            print("🦙 Generating LLM explanations...")
            
            llm_insights = llm_assistant.analyze_and_explain(results)
            results["llm_summary"] = llm_insights["summary"]
            results["llm_explanations"] = llm_insights["detailed_explanations"]
            results["llm_enabled"] = True
        else:
            results["llm_enabled"] = False
            if not LLM_ENABLED:
                results["llm_message"] = "LLM not available. Install Ollama and pull llama3.1:8b"
        
        print(f"✅ Analysis completed successfully")
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/v1/change-detection")
async def detect_changes(request: ChangeDetectionRequest):
    """
    Detect changes between two time periods with LLM interpretation
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
            raise HTTPException(
                status_code=404,
                detail="Could not find imagery for one or both periods"
            )
        
        # Calculate changes
        before_ndvi = before_results["analyses"]["vegetation_health"]["statistics"]["mean_ndvi"]
        after_ndvi = after_results["analyses"]["vegetation_health"]["statistics"]["mean_ndvi"]
        
        ndvi_change = after_ndvi - before_ndvi
        percent_change = (ndvi_change / before_ndvi * 100) if before_ndvi != 0 else 0
        
        # Basic interpretation
        if ndvi_change < -0.1:
            basic_interpretation = f"Significant vegetation loss detected ({percent_change:.1f}% decrease). Possible deforestation, drought, or urban expansion."
        elif ndvi_change > 0.1:
            basic_interpretation = f"Vegetation increase detected ({percent_change:.1f}% increase). Possible reforestation, agricultural growth, or seasonal changes."
        else:
            basic_interpretation = "Minimal change in vegetation cover. Conditions remain relatively stable."
        
        change_data = {
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
                "basic_interpretation": basic_interpretation
            },
            "data_source": "Microsoft Planetary Computer (Sentinel-2) - FREE",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add LLM interpretation
        if request.include_llm_explanation and LLM_ENABLED:
            print("🦙 Generating LLM change interpretation...")
            llm_interpretation = llm_assistant.llm.interpret_change_detection(change_data)
            change_data["llm_interpretation"] = llm_interpretation
            change_data["llm_enabled"] = True
        else:
            change_data["llm_enabled"] = False
        
        return change_data
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Change detection failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Change detection failed: {str(e)}")

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """
    Conversational interface - ask questions about geospatial analysis
    """
    if not LLM_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Please install Ollama and pull llama3.1:8b"
        )
    
    try:
        print(f"\n💬 Chat request: {request.message}")
        
        response = llm_assistant.process_natural_query(
            query=request.message,
            analysis_results=request.context
        )
        
        return {
            "status": "success",
            "query": request.message,
            "response": response,
            "model": "llama3.1:8b",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/api/v1/query")
async def process_query(request: QueryRequest):
    """
    Parse natural language query and suggest analysis parameters
    """
    if not LLM_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Please install Ollama and pull llama3.1:8b"
        )
    
    try:
        print(f"\n🔍 Query parsing: {request.query}")
        
        parameters = llm_assistant.llm.extract_query_parameters(request.query)
        
        return {
            "status": "success",
            "original_query": request.query,
            "extracted_parameters": parameters,
            "suggestions": {
                "message": "Use these parameters for /api/v1/analyze endpoint",
                "note": "Adjust coordinates based on actual location"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Query parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query parsing failed: {str(e)}")

@app.get("/api/v1/llm/status")
async def llm_status():
    """Check LLM availability"""
    return {
        "llm_enabled": LLM_ENABLED,
        "model": "llama3.1:8b" if LLM_ENABLED else None,
        "status": "ready" if LLM_ENABLED else "unavailable",
        "setup_instructions": None if LLM_ENABLED else {
            "steps": [
                "Install Ollama: curl -fsSL https://ollama.com/install.sh | sh",
                "Start Ollama: ollama serve",
                "Pull model: ollama pull llama3.1:8b",
                "Restart this API"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Starting GeoGPT Analysis API with LLM")
    print("   Data Source: Microsoft Planetary Computer (FREE)")
    print(f"   LLM: {'Llama 3.1 (8B) ✅' if LLM_ENABLED else 'Disabled ⚠️'}")
    print("   Billing: NOT REQUIRED - 100% FREE!")
    print("   Port: 8002")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)