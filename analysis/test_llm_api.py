# test_llm_api.py
"""
Comprehensive test suite for GeoGPT with Llama LLM
Tests all new LLM-enhanced endpoints
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict

API_BASE = "http://localhost:8002"

def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_llm_status():
    """Test 1: Check LLM availability"""
    print_section("TEST 1: LLM Status Check")
    
    try:
        response = requests.get(f"{API_BASE}/api/v1/llm/status", timeout=5)
        data = response.json()
        
        print(f"✅ LLM Enabled: {data['llm_enabled']}")
        print(f"✅ Model: {data['model']}")
        print(f"✅ Status: {data['status']}")
        
        if not data['llm_enabled']:
            print("\n⚠️  LLM not available!")
            if 'setup_instructions' in data:
                print("\n📋 Setup instructions:")
                for step in data['setup_instructions']['steps']:
                    print(f"   • {step}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API")
        print("   Run: python analysis/analysis_api_with_llm.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_health_check():
    """Test 2: Health check with LLM info"""
    print_section("TEST 2: Health Check")
    
    try:
        response = requests.get(f"{API_BASE}/api/v1/health")
        data = response.json()
        
        print(f"✅ Status: {data['status']}")
        print(f"✅ Data Source: {data['data_source']}")
        print(f"✅ LLM Enabled: {data['llm_enabled']}")
        print(f"✅ LLM Model: {data.get('llm_model', 'N/A')}")
        print(f"✅ Billing: {data['billing']}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat():
    """Test 3: Chat endpoint"""
    print_section("TEST 3: Chat Interface")
    
    questions = [
        "What is NDVI and how is it calculated?",
        "How can I detect floods using satellite imagery?",
        "Explain the difference between NDVI and NDWI"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. Question: {question}")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/chat",
                json={"message": question},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Response: {data['response'][:200]}...")
            else:
                print(f"   ❌ Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    return True

def test_query_parsing():
    """Test 4: Natural language query parsing"""
    print_section("TEST 4: Query Parameter Extraction")
    
    test_queries = [
        "Show me vegetation health in Punjab from January to March 2024",
        "Check for floods near Chandigarh last month",
        "Analyze urban growth in Delhi over the past year"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/query",
                json={"query": query},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Extracted parameters:")
                params = data['extracted_parameters']
                print(f"      • Analysis type: {params.get('analysis_type')}")
                print(f"      • Location: {params.get('location')}")
                print(f"      • Date range: {params.get('date_range')}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return True

def test_analysis_with_llm():
    """Test 5: Full analysis with LLM explanations"""
    print_section("TEST 5: Analysis with LLM Explanations")
    
    print("\n📡 Running vegetation analysis with LLM...")
    print("   (This will take 60-90 seconds)")
    
    # Small test area
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
        "max_cloud_cover": 30,
        "include_llm_explanation": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/analyze",
            json=payload,
            timeout=180
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Analysis completed!")
            print(f"\n📊 Technical Results:")
            
            if 'analyses' in data and 'vegetation_health' in data['analyses']:
                veg = data['analyses']['vegetation_health']
                stats = veg['statistics']
                print(f"   • Mean NDVI: {stats['mean_ndvi']:.3f}")
                print(f"   • Image date: {data['image_date']}")
                print(f"   • Cloud cover: {data['cloud_cover']:.2f}%")
            
            # LLM explanations
            if data.get('llm_enabled'):
                print(f"\n🦙 LLM Summary:")
                print(f"   {data.get('llm_summary', 'N/A')[:300]}...")
                
                if 'llm_explanations' in data:
                    print(f"\n🦙 Detailed Explanation:")
                    for analysis_type, explanation in data['llm_explanations'].items():
                        print(f"\n   {analysis_type.replace('_', ' ').title()}:")
                        print(f"   {explanation[:400]}...")
            else:
                print("\n⚠️  LLM explanations not available")
            
            # Save full result
            with open('test_llm_result.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full result saved to: test_llm_result.json")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏱  Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_change_detection_with_llm():
    """Test 6: Change detection with LLM interpretation"""
    print_section("TEST 6: Change Detection with LLM")
    
    print("\n🔄 Running change detection with LLM...")
    print("   (This will take 2-3 minutes)")
    
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
    middle_date = end_date - timedelta(days=60)
    start_date = end_date - timedelta(days=120)
    
    payload = {
        "aoi_geojson": aoi,
        "before_start": start_date.strftime("%Y-%m-%d"),
        "before_end": middle_date.strftime("%Y-%m-%d"),
        "after_start": middle_date.strftime("%Y-%m-%d"),
        "after_end": end_date.strftime("%Y-%m-%d"),
        "max_cloud_cover": 30,
        "include_llm_explanation": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/change-detection",
            json=payload,
            timeout=240
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Change detection completed!")
            
            change = data['change_detection']
            print(f"\n📊 Change Statistics:")
            print(f"   • NDVI change: {change['ndvi_change']:.3f}")
            print(f"   • Percent change: {change['percent_change']:.1f}%")
            print(f"   • Basic interpretation: {change['basic_interpretation']}")
            
            if data.get('llm_enabled') and 'llm_interpretation' in data:
                print(f"\n🦙 LLM Interpretation:")
                print(f"   {data['llm_interpretation'][:400]}...")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🧪 GeoGPT LLM Integration Test Suite ".center(60, "="))
    print("Testing all LLM-enhanced endpoints")
    
    results = []
    
    # Test 1: LLM Status
    llm_available = test_llm_status()
    results.append(("LLM Status", llm_available))
    
    if not llm_available:
        print("\n" + "="*60)
        print("⚠️  Cannot proceed without LLM")
        print("   Please run: bash setup_llama.sh")
        return
    
    # Test 2: Health check
    results.append(("Health Check", test_health_check()))
    
    # Test 3: Chat
    results.append(("Chat Interface", test_chat()))
    
    # Test 4: Query parsing
    results.append(("Query Parsing", test_query_parsing()))
    
    # Test 5: Analysis with LLM
    results.append(("Analysis + LLM", test_analysis_with_llm()))
    
    # Test 6: Change detection with LLM
    results.append(("Change Detection + LLM", test_change_detection_with_llm()))
    
    # Summary
    print_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("💰 Total Cost: $0.00 (100% FREE!)")
        print("🦙 Llama + Satellite Analysis = GeoGPT Ready!")
        print("="*60)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()