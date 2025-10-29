# ingestion/gee_ingest.py
import ee, os, json
from datetime import datetime
from sqlitedict import SqliteDict

# Initialize EE (interactive auth if needed)
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()   # follow the interactive URL once
    ee.Initialize()

OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT_DIR, exist_ok=True)
INDEX_DB = os.path.join(os.path.dirname(__file__), "index.sqlite")

def get_sentinel2_collection(aoi, start_date, end_date, max_cloud=20):
    return (ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', max_cloud)))

def compute_ndvi(image):
    return image.normalizedDifference(['B8', 'B4']).rename('NDVI')

def mosaic_and_export(aoi_geojson, start_date, end_date, out_prefix="tile", max_cloud=20):
    aoi = ee.Geometry(aoi_geojson)
    coll = get_sentinel2_collection(aoi, start_date, end_date, max_cloud)
    composite = coll.median().clip(aoi)
    ndvi = compute_ndvi(composite)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    basename = f"{out_prefix}_{timestamp}"
    meta = {
        "id": basename,
        "aoi": aoi_geojson,
        "start_date": start_date,
        "end_date": end_date,
        "created_at": timestamp
    }

    # quick thumbnails (for UI)
    thumb_params = {
        'min': 0, 'max': 3000, 'dimensions': 512,
        'region': aoi_geojson['coordinates'],
        'bands': ['B4','B3','B2']
    }
    ndvi_params = {
        'min': -1, 'max': 1, 'dimensions': 512,
        'region': aoi_geojson['coordinates'],
        'format': 'png',
        'bands': ['NDVI']
    }
    composite_with_ndvi = composite.addBands(ndvi)
    meta['thumb_url'] = composite.getThumbURL(thumb_params)
    meta['ndvi_thumb_url'] = composite_with_ndvi.select('NDVI').getThumbURL(ndvi_params)

    # simple stats (ask GEE to reduce)
    mean_ndvi = ndvi.reduceRegion(ee.Reducer.mean(), aoi, 30).get('NDVI').getInfo()
    meta['mean_ndvi'] = mean_ndvi

    # save metadata to file and index
    meta_path = os.path.join(OUT_DIR, f"{basename}.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    # add to sqlite index
    with SqliteDict(os.path.join(os.path.dirname(__file__), "index.sqlite"), autocommit=True) as db:
        db[basename] = meta

    return meta
