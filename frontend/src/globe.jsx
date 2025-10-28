import React, { useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import CesiumNavigation from "cesium-navigation-es6";

// ✅ Your Cesium Ion Access Token
Cesium.Ion.defaultAccessToken =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYmMxMGJhYi04ODQ0LTQ1MWYtYjYxNC1jNDgyZGZjNTlkN2UiLCJpZCI6MzU0NDcyLCJpYXQiOjE3NjE1NzA3ODB9.ee6fK9oa_ScOtBnBnrJKMW1jZk2Zy2be8BUqwvYpIOY";

const API_URL = "http://127.0.0.1:8000/api/v1/satellites";

function Globe() {
  const cesiumContainer = useRef(null);
  const [viewer, setViewer] = useState(null);
  const [satelliteData, setSatelliteData] = useState([]);

  // --- 🌍 Initialize Cesium Viewer ---
  useEffect(() => {
    let cesiumViewer;
    if (cesiumContainer.current) {
      cesiumViewer = new Cesium.Viewer(cesiumContainer.current, {
        //terrain: Cesium.Terrain.fromWorldTerrain(),
        imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 }), // ✅ Blue Marble imagery
        animation: false,
        timeline: false,
        fullscreenButton: true,
        geocoder: true,
        homeButton: true,
        sceneModePicker: true,
        baseLayerPicker: true,
        navigationHelpButton: true,
      });

      // ✅ Enable globe atmosphere and lighting
      cesiumViewer.scene.globe.enableLighting = true;
      cesiumViewer.scene.globe.showGroundAtmosphere = true;
      cesiumViewer.scene.skyAtmosphere.show = true;

      // ✅ Add Cesium Navigation Controls
      // ✅ fixed
    new CesiumNavigation(cesiumViewer, {
      defaultResetView: Cesium.Cartographic.fromDegrees(0, 0, 20000000),
      enableCompass: true,
      enableZoomControls: true,
      enableDistanceLegend: true,
      enableCompassOuterRing: true,
    });


      setViewer(cesiumViewer);
    }

    return () => {
      if (cesiumViewer) cesiumViewer.destroy();
    };
  }, []);

  // --- 🛰 Fetch Satellite Data ---
  useEffect(() => {
  let intervalId;

  async function fetchData() {
    try {
      const response = await fetch(API_URL);
      const data = await response.json();
      setSatelliteData(data.satellites);
    } catch (error) {
      console.error("Failed to fetch satellite data:", error);
    }
  }

  fetchData(); // Initial fetch
  intervalId = setInterval(fetchData, 5000); // Fetch every 5 seconds

  return () => clearInterval(intervalId); // Cleanup on unmount
}, []);

  // --- 🛰 Plot Satellites on Globe ---
  useEffect(() => {
  if (!viewer || satelliteData.length === 0) return;

  satelliteData.forEach((satellite) => {
    const position = Cesium.Cartesian3.fromDegrees(
      satellite.longitude,
      satellite.latitude,
      satellite.altitude * 1000
    );

    const existingEntity = viewer.entities.getById(satellite.norad_id);
    if (existingEntity) {
      existingEntity.position = position;
      existingEntity.properties.altitude = satellite.altitude;
    } else {
      viewer.entities.add({
        id: satellite.norad_id,
        name: satellite.name,
        position: position,
        point: {
          pixelSize: 6,
          color: Cesium.Color.RED,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
        properties: {
          altitude: satellite.altitude,
        },
      });
    }
  });
}, [viewer, satelliteData]);

  // --- 👆 Add User Interaction (click satellite → show label) ---
  useEffect(() => {
    if (!viewer) return;

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    let selectedLabel = null;

    handler.setInputAction(function (movement) {
      if (selectedLabel) {
        viewer.entities.remove(selectedLabel);
        selectedLabel = null;
      }

      const pickedObject = viewer.scene.pick(movement.position);
      if (Cesium.defined(pickedObject) && Cesium.defined(pickedObject.id)) {
        const entity = pickedObject.id;

        if (entity.point) {
          const altitude = entity.properties.altitude.getValue();
          const labelText = `${entity.name}\nAltitude: ${Math.round(
            altitude
          )} km`;

          selectedLabel = viewer.entities.add({
            position: entity.position.getValue(viewer.clock.currentTime),
            label: {
              text: labelText,
              font: "14pt monospace",
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              outlineWidth: 2,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -9),
              fillColor: Cesium.Color.WHITE,
            },
          });
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => handler.destroy();
  }, [viewer]);

  return (
    <div
      className="cesium-container"
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