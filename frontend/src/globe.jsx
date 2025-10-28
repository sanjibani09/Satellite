import React, { useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import CesiumNavigation from "cesium-navigation-es6";

// ✅ Cesium Ion Access Token
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
        imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 }),
        animation: false,
        timeline: false,
        fullscreenButton: true,
        geocoder: true,
        homeButton: true,
        sceneModePicker: true,
        baseLayerPicker: true,
        navigationHelpButton: true,
      });

      cesiumViewer.scene.globe.enableLighting = true;
      cesiumViewer.scene.globe.showGroundAtmosphere = true;
      cesiumViewer.scene.skyAtmosphere.show = true;

      // ✅ Add Navigation Controls
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
        setSatelliteData(data.satellites || []);
      } catch (error) {
        console.error("Failed to fetch satellite data:", error);
      }
    }

    fetchData();
    intervalId = setInterval(fetchData, 5000); // refresh every 5s

    return () => clearInterval(intervalId);
  }, []);

  // --- 🛰 Animate Satellites Around Earth ---
  useEffect(() => {
    if (!viewer || satelliteData.length === 0) return;

    // Clear all entities each update to avoid duplicates
    viewer.entities.removeAll();

    // Collect all timestamps for clock sync
    const allSamples = satelliteData.flatMap((sat) => sat.samples || []);
    if (allSamples.length === 0) return;

    const times = allSamples.map((s) => Cesium.JulianDate.fromDate(new Date(s.t)));
    const start = Cesium.JulianDate.clone(times[0]);
    const stop = Cesium.JulianDate.clone(times[times.length - 1]);

    viewer.clock.startTime = start.clone();
    viewer.clock.stopTime = stop.clone();
    viewer.clock.currentTime = start.clone();
    viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
    viewer.clock.multiplier = 60; // 1s = 1 minute
    viewer.clock.shouldAnimate = true;

    // --- Draw each satellite ---
    satelliteData.forEach((sat) => {
      if (!Array.isArray(sat.samples) || sat.samples.length < 2) return;

      const validSamples = sat.samples.filter(
        (s) =>
          s &&
          typeof s.lat === "number" &&
          typeof s.lon === "number" &&
          typeof s.alt_km === "number" &&
          !isNaN(s.lat) &&
          !isNaN(s.lon) &&
          !isNaN(s.alt_km)
      );
      if (validSamples.length < 2) return;

      const sampledPos = new Cesium.SampledPositionProperty();
      validSamples.forEach((s) => {
        const jd = Cesium.JulianDate.fromDate(new Date(s.t));
        const pos = Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.alt_km * 1000);
        sampledPos.addSample(jd, pos);
      });

      // Short, subtle orbit trail (to avoid messy globe)
      const orbitPositions = validSamples
        .slice(0, Math.floor(validSamples.length / 3)) // show only small segment
        .map((s) =>
          Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.alt_km * 1000)
        );

      viewer.entities.add({
        id: sat.norad_id + "_orbit",
        name: sat.name + " orbit",
        polyline: {
          positions: orbitPositions,
          width: 0.8,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.05,
            color: Cesium.Color.CYAN.withAlpha(0.25),
          }),
        },
      });

      // Moving satellite entity
      viewer.entities.add({
        id: sat.norad_id,
        name: sat.name,
        position: sampledPos,
        point: {
          pixelSize: 7,
          color: Cesium.Color.YELLOW,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
        path: {
          show: true,
          leadTime: 0,
          trailTime: 120, // show short trail behind
          width: 2,
        },
      });
    });

    // Focus the globe view
    viewer.zoomTo(viewer.entities);
  }, [viewer, satelliteData]);

  // --- 👆 Click to show satellite info ---
  useEffect(() => {
    if (!viewer) return;

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    let selectedLabel = null;

    handler.setInputAction((movement) => {
      if (selectedLabel) {
        viewer.entities.remove(selectedLabel);
        selectedLabel = null;
      }

      const picked = viewer.scene.pick(movement.position);
      if (Cesium.defined(picked) && picked.id && picked.id.position) {
        const entity = picked.id;
        const cartesian = entity.position.getValue(viewer.clock.currentTime);
        const carto = Cesium.Cartographic.fromCartesian(cartesian);
        const altitude = carto.height / 1000;

        selectedLabel = viewer.entities.add({
          position: cartesian,
          label: {
            text: `${entity.name}\nAltitude: ${altitude.toFixed(1)} km`,
            font: "14pt monospace",
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -9),
            fillColor: Cesium.Color.WHITE,
          },
        });
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
