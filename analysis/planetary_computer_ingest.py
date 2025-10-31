# analysis/planetary_computer_ingest.py
"""
Free alternative to Google Earth Engine using Microsoft Planetary Computer
No billing required - completely free for everyone!
"""

import planetary_computer as pc
from pystac_client import Client
import rasterio
from rasterio.mask import mask
import numpy as np
from datetime import datetime, timedelta
from shapely.geometry import shape
import json

class PlanetaryComputerClient:
    """
    Free satellite imagery client using Microsoft Planetary Computer
    """
    
    def __init__(self):
        self.catalog = Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace,
        )
        print("✅ Connected to Microsoft Planetary Computer (Free)")
    
    def search_sentinel2(self, aoi_geojson, start_date, end_date, max_cloud_cover=20):
        """Search for Sentinel-2 imagery"""
        print(f"🔍 Searching Sentinel-2 imagery...")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Max cloud cover: {max_cloud_cover}%")
        
        search = self.catalog.search(
            collections=["sentinel-2-l2a"],
            intersects=aoi_geojson,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}}
        )
        
        items = list(search.items())
        print(f"   Found {len(items)} images")
        return items
    
    def get_least_cloudy_image(self, items):
        """Get the image with least cloud cover"""
        if not items:
            return None
        
        sorted_items = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
        best = sorted_items[0]
        print(f"   Selected image from {best.datetime.date()} (cloud cover: {best.properties.get('eo:cloud_cover', 'N/A')}%)")
        return best
    
    def read_band(self, item, band_name, aoi_geojson):
        """Read a specific band for the AOI"""
        band_href = item.assets[band_name].href
        
        with rasterio.open(band_href) as src:
            geom = [aoi_geojson]
            out_image, out_transform = mask(src, geom, crop=True, filled=True, nodata=0)
            return out_image[0]
    
    def calculate_ndvi(self, item, aoi_geojson):
        """Calculate NDVI for the AOI"""
        print("🌱 Calculating NDVI...")
        
        try:
            # Read NIR (B08) and Red (B04) bands
            nir = self.read_band(item, "B08", aoi_geojson).astype(float)
            red = self.read_band(item, "B04", aoi_geojson).astype(float)
            
            # Calculate NDVI
            with np.errstate(divide='ignore', invalid='ignore'):
                ndvi = (nir - red) / (nir + red)
            
            ndvi = np.nan_to_num(ndvi, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Calculate statistics
            valid_pixels = ndvi[ndvi != 0]
            
            if len(valid_pixels) == 0:
                return self._empty_ndvi_result()
            
            stats = {
                "mean_ndvi": float(np.mean(valid_pixels)),
                "median_ndvi": float(np.median(valid_pixels)),
                "std_ndvi": float(np.std(valid_pixels)),
                "min_ndvi": float(np.min(valid_pixels)),
                "max_ndvi": float(np.max(valid_pixels)),
            }
            
            # Classification
            healthy = np.sum(ndvi > 0.6)
            moderate = np.sum((ndvi > 0.3) & (ndvi <= 0.6))
            stressed = np.sum((ndvi > 0.1) & (ndvi <= 0.3))
            barren = np.sum(ndvi <= 0.1)
            total = len(valid_pixels)
            
            classification = {
                "healthy_percentage": (healthy / total * 100) if total > 0 else 0,
                "moderate_percentage": (moderate / total * 100) if total > 0 else 0,
                "stressed_percentage": (stressed / total * 100) if total > 0 else 0,
                "barren_percentage": (barren / total * 100) if total > 0 else 0,
                "healthy_vegetation_km2": (healthy * 0.0001),  # Approximate
            }
            
            return {
                "statistics": stats,
                "classification": classification,
                "ndvi_array": ndvi
            }
        except Exception as e:
            print(f"   Error calculating NDVI: {e}")
            return self._empty_ndvi_result()
    
    def calculate_ndwi(self, item, aoi_geojson):
        """Calculate NDWI (water index)"""
        print("💧 Calculating NDWI...")
        
        try:
            green = self.read_band(item, "B03", aoi_geojson).astype(float)
            nir = self.read_band(item, "B08", aoi_geojson).astype(float)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                ndwi = (green - nir) / (green + nir)
            
            ndwi = np.nan_to_num(ndwi, nan=0.0, posinf=0.0, neginf=0.0)
            
            valid_pixels = ndwi[ndwi != 0]
            water_pixels = np.sum(ndwi > 0)
            total_pixels = len(valid_pixels)
            
            stats = {
                "mean_ndwi": float(np.mean(valid_pixels)) if len(valid_pixels) > 0 else 0,
                "water_coverage_percentage": (water_pixels / total_pixels * 100) if total_pixels > 0 else 0,
                "water_coverage_km2": (water_pixels * 0.0001),
                "water_pixels": int(water_pixels),
                "total_pixels": int(total_pixels)
            }
            
            return {
                "statistics": stats,
                "ndwi_array": ndwi
            }
        except Exception as e:
            print(f"   Error calculating NDWI: {e}")
            return {"statistics": {"mean_ndwi": 0, "water_coverage_percentage": 0, "water_coverage_km2": 0}}
    
    def calculate_ndbi(self, item, aoi_geojson):
        """Calculate NDBI (built-up index)"""
        print("🏙 Calculating NDBI...")
        
        try:
            swir = self.read_band(item, "B11", aoi_geojson).astype(float)
            nir = self.read_band(item, "B08", aoi_geojson).astype(float)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                ndbi = (swir - nir) / (swir + nir)
            
            ndbi = np.nan_to_num(ndbi, nan=0.0, posinf=0.0, neginf=0.0)
            
            valid_pixels = ndbi[ndbi != 0]
            urban_pixels = np.sum(ndbi > 0)
            total_pixels = len(valid_pixels)
            
            stats = {
                "mean_ndbi": float(np.mean(valid_pixels)) if len(valid_pixels) > 0 else 0,
                "urban_coverage_percentage": (urban_pixels / total_pixels * 100) if total_pixels > 0 else 0,
                "urban_area_km2": (urban_pixels * 0.0001),
                "urban_pixels": int(urban_pixels),
                "total_pixels": int(total_pixels)
            }
            
            return {
                "statistics": stats,
                "ndbi_array": ndbi
            }
        except Exception as e:
            print(f"   Error calculating NDBI: {e}")
            return {"statistics": {"mean_ndbi": 0, "urban_coverage_percentage": 0, "urban_area_km2": 0}}
    
    def analyze_region(self, aoi_geojson, start_date, end_date, 
                      analysis_types=["vegetation_health"], max_cloud_cover=30):
        """Complete analysis workflow"""
        print("\n" + "="*60)
        print("🛰  Microsoft Planetary Computer Analysis (FREE)")
        print("="*60)
        
        # Search for imagery
        items = self.search_sentinel2(aoi_geojson, start_date, end_date, max_cloud_cover)
        
        if not items:
            return {
                "status": "error",
                "message": "No imagery found for the specified criteria",
                "suggestions": [
                    "Try a longer date range",
                    "Increase max_cloud_cover threshold (e.g., 50)",
                    "Check if AOI coordinates are valid"
                ]
            }
        
        # Get best image
        best_item = self.get_least_cloudy_image(items)
        
        results = {
            "status": "success",
            "image_date": best_item.datetime.isoformat(),
            "cloud_cover": best_item.properties.get("eo:cloud_cover"),
            "analyses": {}
        }
        
        # Perform requested analyses
        if "vegetation_health" in analysis_types:
            ndvi_results = self.calculate_ndvi(best_item, aoi_geojson)
            results["analyses"]["vegetation_health"] = {
                "analysis_type": "vegetation_health",
                "statistics": ndvi_results["statistics"],
                "classification": ndvi_results["classification"],
                "interpretation": self._interpret_ndvi(ndvi_results["statistics"]["mean_ndvi"])
            }
        
        if "flood_detection" in analysis_types or "water_detection" in analysis_types:
            ndwi_results = self.calculate_ndwi(best_item, aoi_geojson)
            results["analyses"]["water_detection"] = {
                "analysis_type": "water_detection",
                "statistics": ndwi_results["statistics"],
                "interpretation": self._interpret_ndwi(ndwi_results["statistics"]["water_coverage_percentage"])
            }
        
        if "urban_growth" in analysis_types:
            ndbi_results = self.calculate_ndbi(best_item, aoi_geojson)
            results["analyses"]["urban_detection"] = {
                "analysis_type": "urban_detection",
                "statistics": ndbi_results["statistics"],
                "interpretation": self._interpret_ndbi(ndbi_results["statistics"]["urban_coverage_percentage"])
            }
        
        print("\n✅ Analysis complete!")
        print("="*60 + "\n")
        
        return results
    
    def _interpret_ndvi(self, mean_ndvi):
        """Generate human-readable NDVI interpretation"""
        if mean_ndvi > 0.6:
            return "Healthy, dense vegetation cover across the region"
        elif mean_ndvi > 0.4:
            return "Moderate vegetation cover with some stressed areas"
        elif mean_ndvi > 0.2:
            return "Sparse vegetation with significant stress indicators"
        else:
            return "Minimal vegetation; predominantly barren or built-up land"
    
    def _interpret_ndwi(self, water_percentage):
        """Generate human-readable NDWI interpretation"""
        if water_percentage > 30:
            return "Significant water coverage detected - potential flood risk"
        elif water_percentage > 10:
            return "Moderate water bodies present"
        elif water_percentage > 1:
            return "Some water bodies detected"
        else:
            return "Minimal water coverage - normal conditions"
    
    def _interpret_ndbi(self, urban_percentage):
        """Generate human-readable NDBI interpretation"""
        if urban_percentage > 50:
            return "Heavily urbanized area with dense built-up structures"
        elif urban_percentage > 20:
            return "Significant urban development present"
        elif urban_percentage > 5:
            return "Moderate urban settlements detected"
        else:
            return "Minimal built-up area; predominantly natural landscape"
    
    def _empty_ndvi_result(self):
        """Return empty NDVI result"""
        return {
            "statistics": {
                "mean_ndvi": 0,
                "median_ndvi": 0,
                "std_ndvi": 0,
                "min_ndvi": 0,
                "max_ndvi": 0,
            },
            "classification": {
                "healthy_percentage": 0,
                "moderate_percentage": 0,
                "stressed_percentage": 0,
                "barren_percentage": 0,
                "healthy_vegetation_km2": 0,
            },
            "ndvi_array": np.array([])
        }


# Test if run directly
if __name__ == "__main__":
    print("Testing Microsoft Planetary Computer Client...")
    
    client = PlanetaryComputerClient()
    
    test_aoi = {
        "type": "Polygon",
        "coordinates": [[
            [76.7, 30.7],
            [76.8, 30.7],
            [76.8, 30.8],
            [76.7, 30.8],
            [76.7, 30.7]
        ]]
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    results = client.analyze_region(
        aoi_geojson=test_aoi,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        analysis_types=["vegetation_health"],
        max_cloud_cover=30
    )
    
    print(json.dumps(results, indent=2))