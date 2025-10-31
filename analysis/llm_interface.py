# llm_interface.py
"""
LLM Interface for GeoGPT using Llama models via Ollama
Supports conversational queries and analysis interpretation
"""

import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class LlamaModel(Enum):
    """Available Llama models"""
    LLAMA_3_1_8B = "llama3.1:8b"
    LLAMA_3_1_70B = "llama3.1:70b"
    LLAMA_3_2_3B = "llama3.2:3b"

class GeoGPTLLM:
    """
    Main LLM interface for GeoGPT system
    Handles natural language queries and generates insights
    """
    
    def __init__(
        self, 
        model: str = "llama3.1:8b",
        ollama_host: str = "http://localhost:11434"
    ):
        self.model = model
        self.ollama_host = ollama_host
        self.conversation_history = []
        
        # Test connection
        if not self._test_connection():
            raise ConnectionError(
                f"Cannot connect to Ollama at {ollama_host}. "
                "Make sure Ollama is running: 'ollama serve'"
            )
        
        print(f"✅ Connected to Llama model: {model}")
    
    def _test_connection(self) -> bool:
        """Test if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _call_llama(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Call Llama model via Ollama API
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()['message']['content']
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.Timeout:
            return "Error: Request timed out. Try a simpler query."
        except Exception as e:
            return f"Error calling Llama: {str(e)}"
    
    def interpret_vegetation_analysis(self, analysis_data: Dict) -> str:
        """
        Generate natural language interpretation of vegetation analysis
        """
        system_prompt = """You are GeoGPT, an expert geospatial AI assistant specializing in satellite imagery analysis.
Your role is to explain vegetation health analysis results in clear, actionable language.
Focus on practical implications for agriculture, environment, and land management."""

        stats = analysis_data.get('statistics', {})
        classification = analysis_data.get('classification', {})
        
        prompt = f"""Analyze this vegetation health data and provide insights:

**NDVI Statistics:**
- Mean NDVI: {stats.get('mean_ndvi', 0):.3f}
- Median NDVI: {stats.get('median_ndvi', 0):.3f}
- Range: {stats.get('min_ndvi', 0):.3f} to {stats.get('max_ndvi', 0):.3f}

**Vegetation Classification:**
- Healthy vegetation: {classification.get('healthy_percentage', 0):.1f}%
- Moderate health: {classification.get('moderate_percentage', 0):.1f}%
- Stressed vegetation: {classification.get('stressed_percentage', 0):.1f}%
- Barren land: {classification.get('barren_percentage', 0):.1f}%

**Estimated healthy area:** {classification.get('healthy_vegetation_km2', 0):.2f} km²

Provide a 3-4 sentence interpretation covering:
1. Overall vegetation health status
2. Potential causes or concerns
3. Recommended actions or monitoring needs"""

        return self._call_llama(prompt, system_prompt, temperature=0.6)
    
    def interpret_water_analysis(self, analysis_data: Dict) -> str:
        """
        Generate interpretation for water/flood detection
        """
        system_prompt = """You are GeoGPT, specializing in water resource monitoring and flood detection.
Explain water coverage analysis with focus on flood risk, water management, and environmental impact."""

        stats = analysis_data.get('statistics', {})
        
        prompt = f"""Analyze this water detection data:

**Water Index (NDWI) Statistics:**
- Mean NDWI: {stats.get('mean_ndwi', 0):.3f}
- Water coverage: {stats.get('water_coverage_percentage', 0):.1f}%
- Estimated water area: {stats.get('water_coverage_km2', 0):.2f} km²
- Water pixels detected: {stats.get('water_pixels', 0):,}

Provide analysis covering:
1. Water coverage assessment
2. Flood risk level (if any)
3. Comparison to typical conditions
4. Monitoring recommendations"""

        return self._call_llama(prompt, system_prompt, temperature=0.6)
    
    def interpret_urban_analysis(self, analysis_data: Dict) -> str:
        """
        Generate interpretation for urban growth detection
        """
        system_prompt = """You are GeoGPT, specializing in urban planning and development monitoring.
Explain urban area detection with focus on growth patterns, planning implications, and sustainability."""

        stats = analysis_data.get('statistics', {})
        
        prompt = f"""Analyze this urban development data:

**Built-up Index (NDBI) Statistics:**
- Mean NDBI: {stats.get('mean_ndbi', 0):.3f}
- Urban coverage: {stats.get('urban_coverage_percentage', 0):.1f}%
- Estimated urban area: {stats.get('urban_area_km2', 0):.2f} km²
- Urban pixels: {stats.get('urban_pixels', 0):,}

Provide insights on:
1. Current urbanization level
2. Development patterns observed
3. Potential planning considerations
4. Environmental impact notes"""

        return self._call_llama(prompt, system_prompt, temperature=0.6)
    
    def interpret_change_detection(self, change_data: Dict) -> str:
        """
        Generate interpretation for temporal change analysis
        """
        system_prompt = """You are GeoGPT, specializing in temporal change detection and environmental monitoring.
Explain changes between time periods with focus on causes, impacts, and trends."""

        before = change_data.get('before_period', {})
        after = change_data.get('after_period', {})
        change = change_data.get('change_detection', {})
        
        prompt = f"""Analyze this temporal change detection:

**Before Period:** {before.get('date_range', 'N/A')}
- Image date: {before.get('image_date', 'N/A')}
- Mean NDVI: {before.get('mean_ndvi', 0):.3f}

**After Period:** {after.get('date_range', 'N/A')}
- Image date: {after.get('image_date', 'N/A')}
- Mean NDVI: {after.get('mean_ndvi', 0):.3f}

**Change Detected:**
- NDVI change: {change.get('ndvi_change', 0):.3f}
- Percent change: {change.get('percent_change', 0):.1f}%

Provide detailed analysis:
1. Magnitude and significance of change
2. Possible causes (deforestation, agriculture, seasonal, etc.)
3. Environmental implications
4. Recommended follow-up actions"""

        return self._call_llama(prompt, system_prompt, temperature=0.6)
    
    def answer_geospatial_query(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Answer general geospatial questions using available context
        """
        system_prompt = """You are GeoGPT, an expert geospatial AI assistant with deep knowledge of:
- Satellite imagery analysis (Sentinel-2, Landsat, MODIS)
- Remote sensing indices (NDVI, NDWI, NDBI, EVI)
- Land use and land cover classification
- Change detection and temporal analysis
- Environmental monitoring and disaster response

Provide accurate, technical yet accessible answers. If you need specific data to answer properly, ask for it."""

        if context:
            context_str = f"\n\n**Available Data:**\n{json.dumps(context, indent=2)}"
            prompt = query + context_str
        else:
            prompt = query
        
        return self._call_llama(prompt, system_prompt, temperature=0.7)
    
    def generate_analysis_summary(self, full_results: Dict) -> str:
        """
        Generate comprehensive summary of multiple analyses
        """
        system_prompt = """You are GeoGPT, creating executive summaries of geospatial analysis.
Synthesize multiple data sources into clear, actionable insights for decision-makers."""

        analyses = full_results.get('analyses', {})
        
        summary_parts = []
        summary_parts.append(f"**Analysis Date:** {full_results.get('image_date', 'N/A')}")
        summary_parts.append(f"**Cloud Cover:** {full_results.get('cloud_cover', 'N/A')}%")
        summary_parts.append(f"**Data Source:** {full_results.get('data_source', 'N/A')}")
        summary_parts.append("\n**Available Analyses:**")
        
        for analysis_type, data in analyses.items():
            summary_parts.append(f"\n- {analysis_type.replace('_', ' ').title()}")
            if 'statistics' in data:
                for key, value in list(data['statistics'].items())[:3]:
                    summary_parts.append(f"  • {key}: {value}")
        
        prompt = f"""Synthesize this geospatial analysis into a clear executive summary:

{chr(10).join(summary_parts)}

Create a summary with:
1. Overall Assessment (2-3 sentences)
2. Key Findings (3-4 bullet points)
3. Recommended Actions (2-3 suggestions)
4. Monitoring Priorities

Keep it concise but actionable."""

        return self._call_llama(prompt, system_prompt, temperature=0.6, max_tokens=800)
    
    def extract_query_parameters(self, natural_query: str) -> Dict:
        """
        Parse natural language query to extract analysis parameters
        """
        system_prompt = """You are a query parser for a geospatial analysis system.
Extract structured parameters from natural language queries.
Return ONLY a valid JSON object, no other text."""

        prompt = f"""Extract parameters from this geospatial query:

"{natural_query}"

Return JSON with these fields (use null if not mentioned):
{{
    "analysis_type": ["vegetation_health" or "flood_detection" or "urban_growth" or "water_detection"],
    "location": "place name or coordinates",
    "date_range": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
    "specific_concern": "what user wants to know"
}}

JSON:"""

        response = self._call_llama(prompt, system_prompt, temperature=0.3, max_tokens=300)
        
        try:
            # Extract JSON from response
            if '{' in response:
                json_start = response.index('{')
                json_end = response.rindex('}') + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        return {
            "analysis_type": ["vegetation_health"],
            "location": None,
            "date_range": None,
            "specific_concern": natural_query
        }
    
    def chat(self, message: str, include_history: bool = True) -> str:
        """
        Conversational interface with memory
        """
        system_prompt = """You are GeoGPT, a friendly and knowledgeable geospatial AI assistant.
You help users understand satellite imagery, environmental monitoring, and spatial analysis.
Be conversational, helpful, and explain technical concepts clearly."""

        if include_history and self.conversation_history:
            # Build context from history
            history_context = "\n\n**Previous conversation:**\n"
            for entry in self.conversation_history[-3:]:  # Last 3 exchanges
                history_context += f"User: {entry['user']}\nAssistant: {entry['assistant']}\n\n"
            
            full_prompt = history_context + f"User: {message}\nAssistant:"
        else:
            full_prompt = message
        
        response = self._call_llama(full_prompt, system_prompt, temperature=0.8)
        
        # Store in history
        self.conversation_history.append({
            "user": message,
            "assistant": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []


# Convenience wrapper class
class GeoGPTAssistant:
    """
    High-level assistant that combines LLM with analysis capabilities
    """
    
    def __init__(self, llm: Optional[GeoGPTLLM] = None):
        self.llm = llm or GeoGPTLLM()
        print("🌍 GeoGPT Assistant initialized")
    
    def analyze_and_explain(self, analysis_results: Dict) -> Dict:
        """
        Analyze data and generate natural language explanation
        """
        explanations = {}
        
        if 'analyses' in analysis_results:
            for analysis_type, data in analysis_results['analyses'].items():
                if analysis_type == 'vegetation_health':
                    explanations[analysis_type] = self.llm.interpret_vegetation_analysis(data)
                elif analysis_type in ['water_detection', 'flood_detection']:
                    explanations[analysis_type] = self.llm.interpret_water_analysis(data)
                elif analysis_type in ['urban_detection', 'urban_growth']:
                    explanations[analysis_type] = self.llm.interpret_urban_analysis(data)
        
        # Generate overall summary
        summary = self.llm.generate_analysis_summary(analysis_results)
        
        return {
            "summary": summary,
            "detailed_explanations": explanations,
            "raw_results": analysis_results
        }
    
    def process_natural_query(self, query: str, analysis_results: Optional[Dict] = None) -> str:
        """
        Process a natural language query about geospatial data
        """
        if analysis_results:
            return self.llm.answer_geospatial_query(query, context=analysis_results)
        else:
            return self.llm.chat(query)


# Testing function
if __name__ == "__main__":
    print("🧪 Testing GeoGPT LLM Interface...\n")
    
    try:
        # Initialize
        llm = GeoGPTLLM(model="llama3.1:8b")
        assistant = GeoGPTAssistant(llm)
        
        # Test 1: Simple chat
        print("Test 1: Basic conversation")
        response = llm.chat("What is NDVI and why is it important?")
        print(f"Response: {response}\n")
        
        # Test 2: Interpret sample data
        print("Test 2: Vegetation analysis interpretation")
        sample_data = {
            "statistics": {
                "mean_ndvi": 0.65,
                "median_ndvi": 0.68,
                "min_ndvi": 0.2,
                "max_ndvi": 0.85
            },
            "classification": {
                "healthy_percentage": 65.5,
                "moderate_percentage": 20.3,
                "stressed_percentage": 10.2,
                "barren_percentage": 4.0,
                "healthy_vegetation_km2": 125.5
            }
        }
        
        interpretation = llm.interpret_vegetation_analysis(sample_data)
        print(f"Interpretation: {interpretation}\n")
        
        print("✅ All tests passed!")
        
    except ConnectionError as e:
        print(f"❌ {e}")
        print("\n📋 Setup Instructions:")
        print("1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Start Ollama: ollama serve")
        print("3. Pull model: ollama pull llama3.1:8b")
        print("4. Run this script again")