-- Table to store basic information about each satellite
CREATE TABLE satellites (
    id SERIAL PRIMARY KEY, -- Unique identifier for each satellite in our database
    norad_cat_id INT UNIQUE NOT NULL, -- The satellite's unique NORAD catalog number
    name VARCHAR(255) NOT NULL -- Common name for the satellite
);

-- Table to store the TLE data for each satellite
-- A single satellite can have multiple TLEs over time
CREATE TABLE tles (
    id SERIAL PRIMARY KEY, -- Unique identifier for each TLE entry
    satellite_id INT NOT NULL, -- Foreign key linking to the satellites table
    epoch TIMESTAMP WITH TIME ZONE NOT NULL, -- The timestamp (epoch) of the TLE data
    line1 VARCHAR(70) NOT NULL, -- The first line of the TLE
    line2 VARCHAR(70) NOT NULL, -- The second line of the TLE
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- When we fetched this data

    -- Establishes the link between this table and the satellites table
    CONSTRAINT fk_satellite
        FOREIGN KEY(satellite_id)
        REFERENCES satellites(id)
        ON DELETE CASCADE -- If a satellite is deleted, its TLEs are also deleted
);

-- Create an index for faster lookups of TLEs for a specific satellite
CREATE INDEX idx_tles_satellite_id ON tles(satellite_id);