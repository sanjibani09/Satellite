import React, { useState } from 'react';

const AnalysisPanel = ({ onAnalyze, loading, results }) => {
  const [aoi, setAoi] = useState({
    minLat: 30.5,
    maxLat: 31.0,
    minLon: 75.5,
    maxLon: 76.0
  });
  
  const [analysisType, setAnalysisType] = useState('vegetation_health');

  const handleAnalyze = () => {
    // Convert AOI to GeoJSON
    const aoiGeoJSON = {
      type: "Polygon",
      coordinates: [[
        [aoi.minLon, aoi.minLat],
        [aoi.maxLon, aoi.minLat],
        [aoi.maxLon, aoi.maxLat],
        [aoi.minLon, aoi.maxLat],
        [aoi.minLon, aoi.minLat]
      ]]
    };

    // Get date range (last 30 days)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    onAnalyze({
      aoi_geojson: aoiGeoJSON,
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
      analysis_types: [analysisType],
      max_cloud_cover: 20
    });
  };

  return (
    <div style={{
      position: 'absolute',
      top: '80px',
      left: '10px',
      background: 'rgba(0, 0, 0, 0.85)',
      padding: '20px',
      borderRadius: '12px',
      color: 'white',
      fontFamily: 'sans-serif',
      fontSize: '14px',
      width: '320px',
      maxHeight: '80vh',
      overflowY: 'auto',
      zIndex: 1000,
      boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
    }}>
      <h3 style={{ margin: '0 0 15px 0', fontSize: '18px', fontWeight: 'bold' }}>
        🧠 ML Analysis
      </h3>

      {/* AOI Selection */}
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          📍 Area of Interest
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <input
            type="number"
            step="0.1"
            value={aoi.minLat}
            onChange={(e) => setAoi({...aoi, minLat: parseFloat(e.target.value)})}
            placeholder="Min Lat"
            style={{
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #444',
              background: '#222',
              color: 'white'
            }}
          />
          <input
            type="number"
            step="0.1"
            value={aoi.maxLat}
            onChange={(e) => setAoi({...aoi, maxLat: parseFloat(e.target.value)})}
            placeholder="Max Lat"
            style={{
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #444',
              background: '#222',
              color: 'white'
            }}
          />
          <input
            type="number"
            step="0.1"
            value={aoi.minLon}
            onChange={(e) => setAoi({...aoi, minLon: parseFloat(e.target.value)})}
            placeholder="Min Lon"
            style={{
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #444',
              background: '#222',
              color: 'white'
            }}
          />
          <input
            type="number"
            step="0.1"
            value={aoi.maxLon}
            onChange={(e) => setAoi({...aoi, maxLon: parseFloat(e.target.value)})}
            placeholder="Max Lon"
            style={{
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #444',
              background: '#222',
              color: 'white'
            }}
          />
        </div>
      </div>

      {/* Analysis Type */}
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          🔬 Analysis Type
        </label>
        <select
          value={analysisType}
          onChange={(e) => setAnalysisType(e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #444',
            background: '#222',
            color: 'white'
          }}
        >
          <option value="vegetation_health">🌱 Vegetation Health</option>
          <option value="flood_detection">💧 Water/Flood Detection</option>
          <option value="urban_growth">🏙 Urban Growth</option>
        </select>
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={loading}
        style={{
          width: '100%',
          padding: '12px',
          borderRadius: '6px',
          border: 'none',
          background: loading ? '#555' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          fontSize: '16px',
          fontWeight: 'bold',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s'
        }}
      >
        {loading ? '⏳ Analyzing...' : '🚀 Run Analysis'}
      </button>

      {/* Results Display */}
      {results && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          borderLeft: '4px solid #667eea'
        }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>
            📊 Results
          </h4>

          {results.analyses?.vegetation_health && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '5px' }}>
                VEGETATION HEALTH
              </div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '5px' }}>
                NDVI: {results.analyses.vegetation_health.statistics?.NDVI_mean?.toFixed(3)}
              </div>
              <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
                {results.analyses.vegetation_health.interpretation}
              </div>
              <div style={{ marginTop: '8px', fontSize: '12px' }}>
                Healthy: {results.analyses.vegetation_health.classification?.healthy_percentage?.toFixed(1)}%
              </div>
            </div>
          )}

          {results.analyses?.water_detection && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '5px' }}>
                WATER DETECTION
              </div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '5px' }}>
                {results.analyses.water_detection.water_coverage_km2?.toFixed(2)} km²
              </div>
              <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
                {results.analyses.water_detection.interpretation}
              </div>
            </div>
          )}

          {results.analyses?.urban_detection && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '5px' }}>
                URBAN AREAS
              </div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '5px' }}>
                {results.analyses.urban_detection.urban_area_km2?.toFixed(2)} km²
              </div>
              <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
                {results.analyses.urban_detection.interpretation}
              </div>
            </div>
          )}

          {results.thumbnail_url && (
            <div style={{ marginTop: '12px' }}>
              <a
                href={results.thumbnail_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block',
                  padding: '8px 12px',
                  background: '#444',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}
              >
                🖼 View Satellite Image
              </a>
            </div>
          )}
        </div>
      )}

      {/* Instructions */}
      <div style={{
        marginTop: '15px',
        padding: '10px',
        background: 'rgba(102, 126, 234, 0.1)',
        borderRadius: '6px',
        fontSize: '12px',
        lineHeight: '1.6'
      }}>
        <strong>💡 Tip:</strong> Click on the globe to select an area, or enter coordinates manually. Analysis takes 30-60 seconds.
      </div>
    </div>
  );
};

export default AnalysisPanel;