-- Create schema for storing ML analysis results
-- Run this after your existing satellite_db setup

-- ===== Analysis Jobs Table =====
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    aoi_geojson JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    analysis_types TEXT[] NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

-- Index for faster lookups
CREATE INDEX idx_analysis_jobs_status ON analysis_jobs(status);
CREATE INDEX idx_analysis_jobs_created_at ON analysis_jobs(created_at DESC);
CREATE INDEX idx_analysis_jobs_aoi ON analysis_jobs USING GIST (ST_GeomFromGeoJSON(aoi_geojson));

-- ===== Analysis Results Table =====
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) REFERENCES analysis_jobs(job_id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,
    confidence FLOAT,
    summary_stats JSONB,
    detections JSONB,
    geojson_output JSONB,
    interpretation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_analysis_results_job_id ON analysis_results(job_id);
CREATE INDEX idx_analysis_results_type ON analysis_results(analysis_type);

-- ===== Detected Features Table (for spatial queries) =====
CREATE TABLE IF NOT EXISTS detected_features (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES analysis_results(id) ON DELETE CASCADE,
    feature_type VARCHAR(50) NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    properties JSONB,
    area_km2 FLOAT,
    confidence FLOAT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index
CREATE INDEX idx_detected_features_geom ON detected_features USING GIST (geom);
CREATE INDEX idx_detected_features_type ON detected_features(feature_type);

-- ===== Change Detection Results Table =====
CREATE TABLE IF NOT EXISTS change_detections (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(100) UNIQUE NOT NULL,
    aoi_geojson JSONB NOT NULL,
    before_start DATE NOT NULL,
    before_end DATE NOT NULL,
    after_start DATE NOT NULL,
    after_end DATE NOT NULL,
    vegetation_loss_km2 FLOAT,
    vegetation_gain_km2 FLOAT,
    net_change_km2 FLOAT,
    change_stats JSONB,
    interpretation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_change_detections_created_at ON change_detections(created_at DESC);

-- ===== Time Series Data Table =====
CREATE TABLE IF NOT EXISTS vegetation_timeseries (
    id SERIAL PRIMARY KEY,
    location_name VARCHAR(200),
    geom GEOMETRY(Point, 4326),
    observation_date DATE NOT NULL,
    ndvi_mean FLOAT,
    ndvi_std FLOAT,
    evi_mean FLOAT,
    ndwi_mean FLOAT,
    ndbi_mean FLOAT,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vegetation_timeseries_date ON vegetation_timeseries(observation_date DESC);
CREATE INDEX idx_vegetation_timeseries_geom ON vegetation_timeseries USING GIST (geom);

-- ===== Alert Rules Table =====
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    aoi_geojson JSONB NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- vegetation_loss, flood, fire, urban_expansion
    threshold_value FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    metadata JSONB
);

-- ===== Alert Events Table =====
CREATE TABLE IF NOT EXISTS alert_events (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE CASCADE,
    severity VARCHAR(20), -- low, medium, high, critical
    alert_message TEXT NOT NULL,
    detected_value FLOAT,
    geojson_location JSONB,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

CREATE INDEX idx_alert_events_triggered_at ON alert_events(triggered_at DESC);
CREATE INDEX idx_alert_events_severity ON alert_events(severity);

-- ===== Views for Easy Querying =====

-- Recent analyses summary
CREATE OR REPLACE VIEW recent_analyses AS
SELECT 
    aj.job_id,
    aj.status,
    aj.created_at,
    aj.completed_at,
    array_agg(DISTINCT ar.analysis_type) as analyses_performed,
    COUNT(DISTINCT ar.id) as num_results,
    ST_AsGeoJSON(ST_GeomFromGeoJSON(aj.aoi_geojson)) as aoi
FROM analysis_jobs aj
LEFT JOIN analysis_results ar ON aj.job_id = ar.job_id
GROUP BY aj.job_id, aj.status, aj.created_at, aj.completed_at, aj.aoi_geojson
ORDER BY aj.created_at DESC
LIMIT 50;

-- Active alerts summary
CREATE OR REPLACE VIEW active_alerts AS
SELECT 
    ar.rule_name,
    ar.alert_type,
    COUNT(ae.id) as num_events,
    MAX(ae.triggered_at) as last_triggered,
    SUM(CASE WHEN ae.acknowledged = FALSE THEN 1 ELSE 0 END) as unacknowledged_count
FROM alert_rules ar
LEFT JOIN alert_events ae ON ar.id = ae.rule_id
WHERE ar.is_active = TRUE
GROUP BY ar.id, ar.rule_name, ar.alert_type
HAVING COUNT(ae.id) > 0
ORDER BY last_triggered DESC;

-- Detected features summary by type
CREATE OR REPLACE VIEW features_by_type AS
SELECT 
    feature_type,
    COUNT(*) as total_features,
    SUM(area_km2) as total_area_km2,
    AVG(confidence) as avg_confidence,
    MAX(detected_at) as most_recent_detection
FROM detected_features
GROUP BY feature_type
ORDER BY total_features DESC;

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Add comments for documentation
COMMENT ON TABLE analysis_jobs IS 'Stores metadata for analysis job requests';
COMMENT ON TABLE analysis_results IS 'Stores ML analysis outputs and interpretations';
COMMENT ON TABLE detected_features IS 'Stores individual detected features with geometries';
COMMENT ON TABLE change_detections IS 'Stores change detection comparisons between time periods';
COMMENT ON TABLE vegetation_timeseries IS 'Time series data for vegetation indices at specific locations';
COMMENT ON TABLE alert_rules IS 'User-defined rules for automated alerts';
COMMENT ON TABLE alert_events IS 'Triggered alert events based on rules';