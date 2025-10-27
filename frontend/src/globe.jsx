import React, { useEffect, useRef, useState } from "react";
import "cesium/Build/Cesium/Widgets/widgets.css";
import * as Cesium from "cesium";

// --- Cesium Ion Token ---
Cesium.Ion.defaultAccessToken =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI2YzY3NDdhMy1iYjIwLTQxZWMtYmM1NC0zNzM0NTQwYmU1NTQiLCJpZCI6MzQ1MTYwLCJpYXQiOjE3NjE0ODk3Mjl9.jLOoA_VTcvD_Oi5qknsTUdD8QqTA0I9widi0FXsZhHI";

// --- API URL ---
const API_URL = "http://127.0.0.1:8000/api/v1/satellites";

function Globe() {
  const cesiumContainer = useRef(null);
  const [viewer, setViewer] = useState(null);

  // Store entities by NORAD ID for quick updates
  const entityMap = useRef({});

  // ---------- Initialize the Viewer ----------
  useEffect(() => {
    let cesiumViewer;
    if (cesiumContainer.current) {
      cesiumViewer = new Cesium.Viewer(cesiumContainer.current, {
        baseLayerPicker: false,
        geocoder: false,
        animation: false,
        timeline: false,
        fullscreenButton: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
      });

      // Base imagery
      cesiumViewer.imageryLayers.add(Cesium.ImageryLayer.fromWorldImagery());

      // Camera position
      cesiumViewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(77.2, 28.6, 2500000),
      });

      // Async terrain
      setTimeout(async () => {
        try {
          const terrain = await Cesium.createWorldTerrainAsync();
          if (cesiumViewer && !cesiumViewer.isDestroyed()) {
            cesiumViewer.terrainProvider = terrain;
            console.log("✅ Terrain loaded");
          }
        } catch (err) {
          console.warn("⚠️ Terrain load failed:", err);
        }
      }, 1000);

      setViewer(cesiumViewer);
    }

    return () => cesiumViewer && cesiumViewer.destroy();
  }, []);

  // ---------- Fetch Satellite Data ----------
  useEffect(() => {
    if (!viewer) return;

    async function fetchAndUpdate() {
      try {
        const response = await fetch(API_URL);
        const data = await response.json();
        const satellites = data.satellites;

        satellites.forEach((sat) => {
          const altitudeInMeters = sat.altitude * 1000;
          const newPosition = Cesium.Cartesian3.fromDegrees(
            sat.longitude,
            sat.latitude,
            altitudeInMeters
          );

          // If entity already exists → update position
          if (entityMap.current[sat.norad_id]) {
            entityMap.current[sat.norad_id].position = newPosition;
          } else {
            // Otherwise create new entity
            const entity = viewer.entities.add({
              id: sat.norad_id.toString(),
              name: sat.name,
              position: newPosition,
              point: {
                pixelSize: 6,
                color: Cesium.Color.RED,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
              },
              label: {
                text: sat.name,
                font: "12px sans-serif",
                fillColor: Cesium.Color.WHITE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -10),
              },
            });
            entityMap.current[sat.norad_id] = entity;
          }
        });

        console.log("🛰 Updated satellite positions");
      } catch (err) {
        console.error("❌ Fetch failed:", err);
      }
    }

    // Initial fetch
    fetchAndUpdate();

    // Refresh every 10 seconds
    const interval = setInterval(fetchAndUpdate, 10000);
    return () => clearInterval(interval);
  }, [viewer]);

  return (
    <div
      ref={cesiumContainer}
      style={{
        width: "100vw",
        height: "100vh",
        margin: 0,
        padding: 0,
        overflow: "hidden",
      }}
    />
  );
}

export default Globe;
