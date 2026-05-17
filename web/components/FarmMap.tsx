"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Polygon, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const SATELLITE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const SATELLITE_ATTR =
  "&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community";
const OSM_ATTR = "&copy; <a href='https://openstreetmap.org/copyright'>OpenStreetMap</a>";

const TL_COLORS: Record<string, string> = {
  verde: "#1a9850",
  amarillo: "#fdae61",
  rojo: "#d73027",
};

function polygonStyle(trafficLight: string | null) {
  const c = TL_COLORS[trafficLight ?? ""] ?? "#999";
  return {
    color: c,
    weight: 3,
    fillColor: c,
    fillOpacity: 0.25,
  };
}

function FitBoundsControl({ geometry }: { geometry: string | null }) {
  const map = useMap();
  const fitted = useRef(false);

  useEffect(() => {
    if (fitted.current || !geometry) return;
    try {
      const geo = JSON.parse(geometry);
      if (geo.type === "Polygon") {
        const bounds = L.geoJSON(geo).getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40] });
          fitted.current = true;
        }
      }
    } catch {
      // fallback
    }
  }, [map, geometry]);

  return null;
}

function ToggleTileLayer({ satellite }: { satellite: boolean }) {
  const map = useMap();

  useEffect(() => {
    const toRemove: L.TileLayer[] = [];
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer && layer.options.attribution !== "gee-classification") {
        toRemove.push(layer);
      }
    });
    toRemove.forEach((l) => map.removeLayer(l));
    L.tileLayer(satellite ? SATELLITE_URL : OSM_URL, {
      attribution: satellite ? SATELLITE_ATTR : OSM_ATTR,
      maxZoom: 19,
    }).addTo(map);
  }, [satellite, map]);

  return null;
}

function ClassificationOverlay({ url }: { url: string | null }) {
  const map = useMap();
  const layerRef = useRef<L.TileLayer | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }
    if (!url) return;
    const layer = L.tileLayer(url, {
      attribution: "gee-classification",
      opacity: 0.65,
      maxZoom: 19,
    }).addTo(map);
    layerRef.current = layer;
  }, [url, map]);

  return null;
}

function parseGeometry(geometry: string | null): any {
  if (!geometry) return null;
  try {
    const parsed = JSON.parse(geometry);
    if (parsed.type === "Polygon") return parsed;
    if (parsed.type === "MultiPolygon") return parsed;
    if (parsed.type === "Feature" && parsed.geometry) return parsed.geometry;
    if (parsed.type === "FeatureCollection" && parsed.features?.[0]?.geometry) {
      return parsed.features[0].geometry;
    }
    return null;
  } catch {
    return null;
  }
}

export default function FarmMap({
  geometry,
  lat,
  lon,
  trafficLight = null,
  tileUrl = null,
  satellite: initialSatellite = true,
}: {
  geometry: string | null;
  lat: number | null;
  lon: number | null;
  trafficLight?: string | null;
  tileUrl?: string | null;
  satellite?: boolean;
}) {
  const [satellite, setSatellite] = useState(initialSatellite);
  const geoJson = useMemo(() => parseGeometry(geometry), [geometry]);
  const center: [number, number] =
    lat != null && lon != null ? [lat, lon] : [12.5, -85.5];
  const zoom = geoJson ? 16 : 13;

  return (
    <div className="farm-map-container">
      <div className="farm-map-tools">
        <button
          className={`farm-map-btn ${satellite ? "active" : ""}`}
          onClick={() => setSatellite(true)}
          type="button"
        >
          <i className="fa-solid fa-satellite" />
          Satélite
        </button>
        <button
          className={`farm-map-btn ${!satellite ? "active" : ""}`}
          onClick={() => setSatellite(false)}
          type="button"
        >
          <i className="fa-solid fa-map" />
          Mapa
        </button>
      </div>
      <MapContainer
        center={center}
        zoom={zoom}
        className="farm-map"
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <ToggleTileLayer satellite={satellite} />
        <ClassificationOverlay url={tileUrl} />
        <FitBoundsControl geometry={geometry} />
        {geoJson ? (
          <GeoJSON
            key={geometry}
            data={geoJson}
            style={() => polygonStyle(trafficLight)}
          />
        ) : lat != null && lon != null ? (
          <Polygon
            positions={[
              [lat - 0.0005, lon - 0.0005],
              [lat - 0.0005, lon + 0.0005],
              [lat + 0.0005, lon + 0.0005],
              [lat + 0.0005, lon - 0.0005],
            ]}
            pathOptions={polygonStyle(trafficLight)}
          />
        ) : null}
      </MapContainer>
    </div>
  );
}
