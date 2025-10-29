import React, { useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import CesiumNavigation from "cesium-navigation-es6";

Cesium.Ion.defaultAccessToken =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYmMxMGJhYi04ODQ0LTQ1MWYtYjYxNC1jNDgyZGZjNTlkN2UiLCJpZCI6MzU0NDcyLCJpYXQiOjE3NjE1NzA3ODB9.ee6fK9oa_ScOtBnBnrJKMW1jZk2Zy2be8BUqwvYpIOY";

const API_URL = "http://127.0.0.1:8000/api/v1/satellites";

function Globe() {
  const cesiumContainer = useRef(null);
  const [viewer, setViewer] = useState(null);
  const [satelliteData, setSatelliteData] = useState([]);
  const [showGroundStations, setShowGroundStations] = useState(true);
  const [showCoverage, setShowCoverage] = useState(true);
  const hasZoomed = useRef(false);

  // Sample ground stations (you can fetch from API later)
  const groundStations = [
    { name: "Svalbard", lat: 78.2297, lon: 15.3926 },
    { name: "Kiruna", lat: 67.8558, lon: 20.2253 },
    { name: "Fairbanks", lat: 64.8378, lon: -147.7164 },
    { name: "Poker Flat", lat: 65.1295, lon: -147.4791 },
    { name: "Wallops", lat: 37.9403, lon: -75.4664 },
    { name: "Santiago", lat: -33.1489, lon: -70.6693 },
    { name: "Hartebeesthoek", lat: -25.8872, lon: 27.7073 },
    { name: "Dongara", lat: -29.2465, lon: 115.0005 },
    { name: "Singapore", lat: 1.3521, lon: 103.8198 },
    { name: "McMurdo", lat: -77.8419, lon: 166.6863 },
  ];

  // 🌍 Initialize Cesium Viewer
  useEffect(() => {
    if (!cesiumContainer.current) return;

    const cesiumViewer = new Cesium.Viewer(cesiumContainer.current, {
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

    new CesiumNavigation(cesiumViewer, {
      defaultResetView: Cesium.Cartographic.fromDegrees(0, 0, 20000000),
      enableCompass: true,
      enableZoomControls: true,
      enableDistanceLegend: true,
      enableCompassOuterRing: true,
    });

    cesiumViewer.scene.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(0.0, 0.0, 20000000),
    });

    setViewer(cesiumViewer);
    return () => cesiumViewer.destroy();
  }, []);

  // 🛰 Fetch Satellite Data
  useEffect(() => {
    let intervalId;
    async function fetchData() {
      try {
        const res = await fetch(API_URL);
        const data = await res.json();
        setSatelliteData(data.satellites || []);
      } catch (err) {
        console.error("Fetch error:", err);
      }
    }
    fetchData();
    intervalId = setInterval(fetchData, 30000);
    return () => clearInterval(intervalId);
  }, []);

  // 📡 Add Ground Stations
  useEffect(() => {
    if (!viewer) return;

    // Remove old ground stations
    const stationsToRemove = viewer.entities.values.filter((entity) => {
      const id = entity.id;
      return typeof id === "string" && id.startsWith("ground_station_");
    });
    stationsToRemove.forEach((entity) => viewer.entities.remove(entity));

    if (!showGroundStations) return;

    groundStations.forEach((station, idx) => {
      viewer.entities.add({
        id: `ground_station_${idx}`,
        name: station.name,
        position: Cesium.Cartesian3.fromDegrees(station.lon, station.lat, 0),
        billboard: {
          image: createGroundStationIcon(),
          scale: 0.5,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        },
        label: {
          text: station.name,
          font: "12pt sans-serif",
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.TOP,
          pixelOffset: new Cesium.Cartesian2(0, 5),
          fillColor: Cesium.Color.WHITE,
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.5),
          backgroundPadding: new Cesium.Cartesian2(7, 5),
        },
      });
    });
  }, [viewer, showGroundStations]);

  // 🛰 Animate Satellites & Coverage
  useEffect(() => {
    if (!viewer || satelliteData.length === 0) return;

    // Remove old satellite entities
    const entitiesToRemove = viewer.entities.values.filter((entity) => {
      const id = entity.id;
      return (
        typeof id === "string" &&
        !id.endsWith("_orbit") &&
        !id.startsWith("ground_station_") &&
        !id.endsWith("_coverage")
      );
    });

    entitiesToRemove.forEach((entity) => viewer.entities.remove(entity));

    const now = Cesium.JulianDate.now();

    viewer.clock.currentTime = now.clone();
    viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
    viewer.clock.multiplier = 1;
    viewer.clock.shouldAnimate = true;

    let earliestTime = null;
    let latestTime = null;

    satelliteData.forEach((sat) => {
      if (!Array.isArray(sat.samples) || sat.samples.length < 2) return;

      const valid = sat.samples.filter(
        (s) =>
          s &&
          typeof s.lat === "number" &&
          typeof s.lon === "number" &&
          typeof s.alt_km === "number"
      );
      if (valid.length < 2) return;

      // Remove old entities for this specific satellite
      const satId = String(sat.norad_id);
      const orbitId = satId + "_orbit";
      const coverageId = satId + "_coverage";
      const existingSat = viewer.entities.getById(satId);
      if (existingSat) viewer.entities.remove(existingSat);
      const existingOrbit = viewer.entities.getById(orbitId);
      if (existingOrbit) viewer.entities.remove(existingOrbit);
      const existingCoverage = viewer.entities.getById(coverageId);
      if (existingCoverage) viewer.entities.remove(existingCoverage);

      // Create orbit path
      const orbitPositions = valid.map((s) =>
        Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.alt_km * 1000)
      );

      viewer.entities.add({
        id: orbitId,
        name: sat.name + " orbit",
        polyline: {
          positions: orbitPositions,
          width: 1.2,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.05,
            color: Cesium.Color.CYAN.withAlpha(0.25),
          }),
        },
      });

      // Create moving satellite with time-based position
      const sampledPos = new Cesium.SampledPositionProperty();

      sampledPos.setInterpolationOptions({
        interpolationDegree: 5,
        interpolationAlgorithm: Cesium.LagrangePolynomialApproximation,
      });

      let startTime, endTime;

      valid.forEach((s, index) => {
        const jd = Cesium.JulianDate.fromDate(new Date(s.t));
        const pos = Cesium.Cartesian3.fromDegrees(
          s.lon,
          s.lat,
          s.alt_km * 1000
        );
        sampledPos.addSample(jd, pos);

        if (index === 0) startTime = jd.clone();
        if (index === valid.length - 1) endTime = jd.clone();

        if (!earliestTime || Cesium.JulianDate.lessThan(jd, earliestTime)) {
          earliestTime = jd.clone();
        }
        if (!latestTime || Cesium.JulianDate.greaterThan(jd, latestTime)) {
          latestTime = jd.clone();
        }
      });

      // Add satellite entity
      viewer.entities.add({
        id: satId,
        name: sat.name,
        position: sampledPos,
        availability: new Cesium.TimeIntervalCollection([
          new Cesium.TimeInterval({
            start: startTime,
            stop: endTime,
          }),
        ]),
        point: {
          pixelSize: 7,
          color: Cesium.Color.YELLOW,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
        path: {
          show: true,
          leadTime: 0,
          trailTime: 600,
          width: 2,
          material: Cesium.Color.YELLOW.withAlpha(0.5),
        },
      });

      // Add coverage footprint
      if (showCoverage) {
        const avgAltKm =
          valid.reduce((sum, s) => sum + s.alt_km, 0) / valid.length;
        const coverageRadiusKm = calculateCoverageRadius(avgAltKm);

        viewer.entities.add({
          id: coverageId,
          name: sat.name + " coverage",
          position: sampledPos,
          availability: new Cesium.TimeIntervalCollection([
            new Cesium.TimeInterval({
              start: startTime,
              stop: endTime,
            }),
          ]),
          ellipse: {
            semiMinorAxis: coverageRadiusKm * 1000,
            semiMajorAxis: coverageRadiusKm * 1000,
            height: 0,
            material: Cesium.Color.CYAN.withAlpha(0.15),
            outline: true,
            outlineColor: Cesium.Color.CYAN.withAlpha(0.4),
            outlineWidth: 1,
          },
        });
      }
    });

    // Set clock bounds
    if (earliestTime && latestTime) {
      viewer.clock.startTime = earliestTime.clone();
      viewer.clock.stopTime = latestTime.clone();

      if (
        Cesium.JulianDate.greaterThanOrEquals(now, earliestTime) &&
        Cesium.JulianDate.lessThanOrEquals(now, latestTime)
      ) {
        viewer.clock.currentTime = now.clone();
      } else {
        viewer.clock.currentTime = earliestTime.clone();
      }
    }

    // Zoom to satellites once
    if (!hasZoomed.current && viewer.entities.values.length > 0) {
      viewer.zoomTo(viewer.entities);
      hasZoomed.current = true;
    }
  }, [viewer, satelliteData, showCoverage]);

  // 👆 Click to show satellite info
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
      if (Cesium.defined(picked) && picked.id?.position) {
        const entity = picked.id;
        const position = entity.position.getValue(viewer.clock.currentTime);

        if (position) {
          const carto = Cesium.Cartographic.fromCartesian(position);
          const alt = carto.height / 1000;

          selectedLabel = viewer.entities.add({
            position: position,
            label: {
              text: `${entity.name}\nAltitude: ${alt.toFixed(1)} km`,
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

  // Helper function to create ground station icon
  function createGroundStationIcon() {
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");

    // Draw antenna
    ctx.fillStyle = "#FF6B35";
    ctx.beginPath();
    ctx.arc(32, 48, 8, 0, Math.PI * 2);
    ctx.fill();

    // Draw dish
    ctx.strokeStyle = "#FF6B35";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(32, 32, 16, 0, Math.PI, true);
    ctx.stroke();

    // Draw stand
    ctx.fillStyle = "#FF6B35";
    ctx.fillRect(30, 32, 4, 16);

    return canvas.toDataURL();
  }

  // Calculate coverage radius based on altitude
  function calculateCoverageRadius(altitudeKm) {
    const earthRadius = 6371;
    const elevationAngle = 5; // minimum elevation angle in degrees
    const elevationRad = (elevationAngle * Math.PI) / 180;

    const maxRange =
      Math.sqrt(
        Math.pow(earthRadius + altitudeKm, 2) -
          Math.pow(earthRadius * Math.cos(elevationRad), 2)
      ) -
      earthRadius * Math.sin(elevationRad);

    return maxRange;
  }

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <div
        ref={cesiumContainer}
        style={{
          width: "100%",
          height: "100%",
          overflow: "hidden",
          margin: 0,
          padding: 0,
        }}
      />

      {/* Layer Controls */}
      <div
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          background: "rgba(0, 0, 0, 0.7)",
          padding: "15px",
          borderRadius: "8px",
          color: "white",
          fontFamily: "sans-serif",
          fontSize: "14px",
          zIndex: 1000,
        }}
      >
        <div style={{ marginBottom: "10px", fontWeight: "bold" }}>
          Context Layers
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: "8px",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={showGroundStations}
            onChange={(e) => setShowGroundStations(e.target.checked)}
            style={{ marginRight: "8px" }}
          />
          Ground Stations
        </label>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={showCoverage}
            onChange={(e) => setShowCoverage(e.target.checked)}
            style={{ marginRight: "8px" }}
          />
          Coverage Footprints
        </label>
      </div>
    </div>
  );
}

export default Globe;