#!/usr/bin/env python3
"""Quick test of Microsoft Planetary Computer connection"""

import planetary_computer as pc
from pystac_client import Client
from datetime import datetime, timedelta

print("🌍 Testing Microsoft Planetary Computer connection...\n")

try:
    # Connect to catalog
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    print("✅ Connected to Microsoft Planetary Computer")
    
    # Test search for small area
    aoi = {
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
    
    print(f"🔍 Searching for imagery...")
    print(f"   Date range: {start_date.date()} to {end_date.date()}")
    
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=aoi,
        datetime=f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
        limit=5
    )
    
    items = list(search.items())
    print(f"✅ Found {len(items)} Sentinel-2 images")
    
    if items:
        print(f"\n📊 Latest image details:")
        print(f"   Date: {items[0].datetime.date()}")
        print(f"   Cloud cover: {items[0].properties.get('eo:cloud_cover', 'N/A')}%")
    
    print("\n" + "="*60)
    print("🎉 Microsoft Planetary Computer is working!")
    print("💰 Cost: $0.00 (FREE!)")
    print("="*60)
    print("\n✅ You're ready to start the API!")
    print("   Run: python analysis/analysis_api.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n🔧 Troubleshooting:")
    print("1. Check internet connection")
    print("2. Verify installations: pip list | grep planetary")
    print("3. Try again in a few minutes (server might be busy)")
    exit(1)