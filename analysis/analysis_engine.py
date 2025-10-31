# analysis/analysis_engine.py
"""
Core ML Analysis Engine for GeoGPT
Handles segmentation, classification, and change detection on satellite imagery
"""

import numpy as np
import torch
import cv2
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape, mapping
import json

class AnalysisType(Enum):
    """Supported analysis types"""
    LAND_COVER = "land_cover"
    CHANGE_DETECTION = "change_detection"
    VEGETATION_HEALTH = "vegetation_health"
    FLOOD_DETECTION = "flood_detection"
    URBAN_GROWTH = "urban_growth"
    FIRE_DETECTION = "fire_detection"

@dataclass
class AnalysisResult:
    """Structured output from ML analysis"""
    analysis_type: AnalysisType
    confidence: float
    detections: List[Dict]  # List of detected features with geometries
    summary_stats: Dict
    metadata: Dict
    geojson: Optional[Dict] = None

class AnalysisEngine:
    """
    Main analysis engine that coordinates different ML models
    """
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.device = device
        self.models = {}
        print(f"🧠 Analysis Engine initialized on {device}")
    
    def analyze_ndvi(self, image_array: np.ndarray, threshold: float = 0.3) -> AnalysisResult:
        """
        Analyze vegetation health using NDVI
        Expected: image_array with NIR and RED bands
        """
        # Assume image_array is [bands, height, width]
        if image_array.shape[0] < 2:
            raise ValueError("Need at least 2 bands for NDVI (NIR, RED)")
        
        nir = image_array[0].astype(float)
        red = image_array[1].astype(float)
        
        # Calculate NDVI
        ndvi = (nir - red) / (nir + red + 1e-8)
        ndvi = np.clip(ndvi, -1, 1)
        
        # Classify vegetation health
        healthy_mask = ndvi > threshold
        stressed_mask = (ndvi > 0.1) & (ndvi <= threshold)
        barren_mask = ndvi <= 0.1
        
        # Calculate statistics
        total_pixels = ndvi.size
        stats = {
            "mean_ndvi": float(np.nanmean(ndvi)),
            "median_ndvi": float(np.nanmedian(ndvi)),
            "healthy_vegetation_pct": float(np.sum(healthy_mask) / total_pixels * 100),
            "stressed_vegetation_pct": float(np.sum(stressed_mask) / total_pixels * 100),
            "barren_land_pct": float(np.sum(barren_mask) / total_pixels * 100),
        }
        
        # Create detections
        detections = [
            {
                "class": "healthy_vegetation",
                "pixel_count": int(np.sum(healthy_mask)),
                "percentage": stats["healthy_vegetation_pct"]
            },
            {
                "class": "stressed_vegetation",
                "pixel_count": int(np.sum(stressed_mask)),
                "percentage": stats["stressed_vegetation_pct"]
            },
            {
                "class": "barren_land",
                "pixel_count": int(np.sum(barren_mask)),
                "percentage": stats["barren_land_pct"]
            }
        ]
        
        return AnalysisResult(
            analysis_type=AnalysisType.VEGETATION_HEALTH,
            confidence=0.95,  # NDVI is deterministic
            detections=detections,
            summary_stats=stats,
            metadata={"threshold": threshold, "method": "NDVI"}
        )
    
    def detect_water_bodies(self, image_array: np.ndarray, threshold: float = 0.0) -> AnalysisResult:
        """
        Detect water bodies using NDWI (Normalized Difference Water Index)
        Requires GREEN and NIR bands
        """
        if image_array.shape[0] < 2:
            raise ValueError("Need at least GREEN and NIR bands for NDWI")
        
        green = image_array[0].astype(float)
        nir = image_array[1].astype(float)
        
        # Calculate NDWI
        ndwi = (green - nir) / (green + nir + 1e-8)
        ndwi = np.clip(ndwi, -1, 1)
        
        # Water mask
        water_mask = ndwi > threshold
        
        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        water_mask_clean = cv2.morphologyEx(
            water_mask.astype(np.uint8), 
            cv2.MORPH_CLOSE, 
            kernel
        )
        
        # Find contours for individual water bodies
        contours, _ = cv2.findContours(
            water_mask_clean, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        detections = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 100:  # Filter small noise
                detections.append({
                    "id": f"water_body_{i}",
                    "area_pixels": int(area),
                    "perimeter": float(cv2.arcLength(contour, True)),
                    "centroid": self._get_centroid(contour)
                })
        
        total_pixels = ndwi.size
        water_pixels = np.sum(water_mask_clean)
        
        stats = {
            "mean_ndwi": float(np.nanmean(ndwi)),
            "water_coverage_pct": float(water_pixels / total_pixels * 100),
            "num_water_bodies": len(detections),
            "total_water_pixels": int(water_pixels)
        }
        
        return AnalysisResult(
            analysis_type=AnalysisType.FLOOD_DETECTION,
            confidence=0.88,
            detections=detections,
            summary_stats=stats,
            metadata={"threshold": threshold, "method": "NDWI"}
        )
    
    def detect_urban_areas(self, image_array: np.ndarray, threshold: float = 0.0) -> AnalysisResult:
        """
        Detect urban/built-up areas using NDBI (Normalized Difference Built-up Index)
        Requires SWIR and NIR bands
        """
        if image_array.shape[0] < 2:
            raise ValueError("Need SWIR and NIR bands for NDBI")
        
        swir = image_array[0].astype(float)
        nir = image_array[1].astype(float)
        
        # Calculate NDBI
        ndbi = (swir - nir) / (swir + nir + 1e-8)
        ndbi = np.clip(ndbi, -1, 1)
        
        # Urban mask
        urban_mask = ndbi > threshold
        
        # Clean up
        kernel = np.ones((5, 5), np.uint8)
        urban_mask_clean = cv2.morphologyEx(
            urban_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            kernel
        )
        
        total_pixels = ndbi.size
        urban_pixels = np.sum(urban_mask_clean)
        
        stats = {
            "mean_ndbi": float(np.nanmean(ndbi)),
            "urban_coverage_pct": float(urban_pixels / total_pixels * 100),
            "total_urban_pixels": int(urban_pixels)
        }
        
        # Find urban clusters
        contours, _ = cv2.findContours(
            urban_mask_clean,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        detections = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 200:
                detections.append({
                    "id": f"urban_cluster_{i}",
                    "area_pixels": int(area),
                    "centroid": self._get_centroid(contour)
                })
        
        return AnalysisResult(
            analysis_type=AnalysisType.URBAN_GROWTH,
            confidence=0.82,
            detections=detections,
            summary_stats=stats,
            metadata={"threshold": threshold, "method": "NDBI"}
        )
    
    def detect_changes(
        self, 
        before_image: np.ndarray, 
        after_image: np.ndarray,
        threshold: float = 0.2
    ) -> AnalysisResult:
        """
        Detect changes between two time periods
        """
        if before_image.shape != after_image.shape:
            raise ValueError("Images must have same dimensions")
        
        # Calculate difference
        diff = np.abs(after_image.astype(float) - before_image.astype(float))
        
        # Normalize to 0-1
        diff_norm = diff / (np.max(diff) + 1e-8)
        
        # Threshold to get change mask
        change_mask = np.mean(diff_norm, axis=0) > threshold
        
        # Clean up noise
        kernel = np.ones((3, 3), np.uint8)
        change_mask_clean = cv2.morphologyEx(
            change_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            kernel
        )
        
        # Find change regions
        contours, _ = cv2.findContours(
            change_mask_clean,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        detections = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 50:
                detections.append({
                    "id": f"change_region_{i}",
                    "area_pixels": int(area),
                    "centroid": self._get_centroid(contour),
                    "change_intensity": float(np.mean(diff_norm[0][change_mask_clean == 1]))
                })
        
        total_pixels = change_mask.size
        changed_pixels = np.sum(change_mask_clean)
        
        stats = {
            "changed_area_pct": float(changed_pixels / total_pixels * 100),
            "num_change_regions": len(detections),
            "total_changed_pixels": int(changed_pixels),
            "mean_change_intensity": float(np.mean(diff_norm))
        }
        
        return AnalysisResult(
            analysis_type=AnalysisType.CHANGE_DETECTION,
            confidence=0.85,
            detections=detections,
            summary_stats=stats,
            metadata={"threshold": threshold, "method": "pixel_difference"}
        )
    
    @staticmethod
    def _get_centroid(contour) -> Tuple[float, float]:
        """Calculate centroid of a contour"""
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return (0.0, 0.0)
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        return (float(cx), float(cy))
    
    def to_geojson(
        self, 
        result: AnalysisResult, 
        transform, 
        crs: str = "EPSG:4326"
    ) -> Dict:
        """
        Convert analysis result to GeoJSON format
        """
        features = []
        
        for detection in result.detections:
            if "geometry" in detection:
                feature = {
                    "type": "Feature",
                    "properties": {k: v for k, v in detection.items() if k != "geometry"},
                    "geometry": detection["geometry"]
                }
                features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "analysis_type": result.analysis_type.value,
                "confidence": result.confidence,
                "summary_stats": result.summary_stats,
                "metadata": result.metadata
            }
        }
        
        return geojson


# Convenience functions
def analyze_sentinel2_scene(
    image_path: str,
    analysis_types: List[AnalysisType]
) -> List[AnalysisResult]:
    """
    Analyze a Sentinel-2 scene for multiple analysis types
    """
    engine = AnalysisEngine()
    results = []
    
    with rasterio.open(image_path) as src:
        # Read bands (adjust indices based on your data)
        bands = src.read()
        
        for analysis_type in analysis_types:
            if analysis_type == AnalysisType.VEGETATION_HEALTH:
                # Assuming bands are ordered: NIR, RED, ...
                result = engine.analyze_ndvi(bands[[7, 3], :, :])  # B8, B4 for S2
                results.append(result)
            
            elif analysis_type == AnalysisType.FLOOD_DETECTION:
                # GREEN, NIR
                result = engine.detect_water_bodies(bands[[2, 7], :, :])  # B3, B8
                results.append(result)
            
            elif analysis_type == AnalysisType.URBAN_GROWTH:
                # SWIR, NIR
                result = engine.detect_urban_areas(bands[[11, 7], :, :])  # B12, B8
                results.append(result)
    
    return results