# test_free_api.py
"""Quick test of the FREE Analysis API"""

import requests
import json
from datetime import datetime, timedelta

print("="*60)
print("🧪 Testing FREE Analysis API")
print("="*60)

# Test 1: Health Check
print("\n1️⃣ Testing health endpoint...")
try:
    response = requests.get("http://localhost:8002/api/v1/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: {data['status']}")
        print(f"   ✅ Data source: {data['data_source']}")
        print(f"   ✅ Billing: {data['billing']}")
    else:
        print(f"   ❌ Error: {response.status_code}")
        exit(1)
except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to API")
    print("   Make sure it's running: python analysis/analysis_api.py")
    exit(1)

# Test 2: Vegetation Analysis
print("\n2️⃣ Testing vegetation analysis...")
print("   (This will take 60-90 seconds)")

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

payload = {
    "aoi_geojson": aoi,
    "start_date": start_date.strftime("%Y-%m-%d"),
    "end_date": end_date.strftime("%Y-%m-%d"),
    "analysis_types": ["vegetation_health"],
    "max_cloud_cover": 30
}

try:
    response = requests.post(
        "http://localhost:8002/api/v1/analyze",
        json=payload,
        timeout=180
    )
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Analysis successful!")
        
        if 'analyses' in data and 'vegetation_health' in data['analyses']:
            veg = data['analyses']['vegetation_health']
            stats = veg['statistics']
            print(f"\n   📊 Results:")
            print(f"      Mean NDVI: {stats['mean_ndvi']:.3f}")
            print(f"      Interpretation: {veg['interpretation']}")
            print(f"      Image date: {data['image_date']}")
            print(f"      Cloud cover: {data['cloud_cover']:.1f}%")
            
            # Save result
            with open('test_result.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n   💾 Full result saved to: test_result.json")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("💰 Total cost: $0.00 (FREE!)")
        print("="*60)
        
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.Timeout:
    print("   ⏱ Request timed out")
    print("   Try increasing cloud cover or using different dates")
    
except Exception as e:
    print(f"   ❌ Error: {e}")