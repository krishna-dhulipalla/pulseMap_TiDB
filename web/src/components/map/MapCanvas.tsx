// web/src/components/map/MapCanvas.tsx
import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";
import { useEffect, useState } from "react";
import SearchControl from "./controls/SearchControl";
import MyLocationControl from "./controls/MyLocationControl";
import SingleSelect from "./controls/SingleSelect";
import NWSDataLayer from "./overlays/NWSDataLayer";
import EmojiMarker from "./overlays/EmojiMarker";
import { GMAPS_KEY, MAP_ID } from "../../lib/constants";
import { eonetEmoji } from "../../lib/utils";
import type { FC, SelectMeta } from "../../lib/types";
import { ReportIcon } from "../../components/ReportIcon";
import FirmsLayer from "./overlays/FirmsLayer";
import TractsLayer from "./overlays/TractsLayer";
import LegendControl from "./controls/LegendControl";

type RuntimeCfg = {
  VITE_GOOGLE_MAPS_API_KEY?: string;
  VITE_GOOGLE_MAPS_MAP_ID?: string;
};

export default function MapCanvas({
  selectedLL,
  selectedMeta,
  setSelected,
  nws,
  quakes,
  eonet,
  firms,
  reports,
}: {
  selectedLL: [number, number] | null;
  selectedMeta: SelectMeta | null;
  setSelected: (ll: [number, number], meta: SelectMeta) => void;
  nws: FC | null;
  quakes: FC | null;
  eonet: FC | null;
  firms: FC | null;
  reports: FC;
}) {
  const [cfg, setCfg] = useState<RuntimeCfg | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/config/runtime", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then(setCfg)
      .catch((e) => setErr(e.message));
  }, []);

  const apiKey = cfg?.VITE_GOOGLE_MAPS_API_KEY || GMAPS_KEY;
  const mapId = cfg?.VITE_GOOGLE_MAPS_MAP_ID || MAP_ID || undefined;

  if (err) return <div>Map config error: {err}</div>;
  if (!apiKey) return <div>Loading map…</div>;

  return (
    <APIProvider apiKey={apiKey} libraries={["places", "marker", "geometry"]}>
      <Map
        className="map"
        mapId={mapId}
        defaultCenter={{ lat: 39, lng: -98 }}
        defaultZoom={4}
        gestureHandling="greedy"
        disableDefaultUI={false}
      >
        <SearchControl onPlace={setSelected} />
        <MyLocationControl onLocated={setSelected} />
        <SingleSelect onPick={setSelected} />
        <NWSDataLayer
          nws={nws}
          onSelect={(ll, meta) => setSelected(ll, meta)}
        />
        <FirmsLayer
          firms={firms}
          onSelect={(ll, meta) => setSelected(ll, meta)}
        />
        <LegendControl />
        <TractsLayer
          reports={reports}
          eonet={eonet}
          quakes={quakes}
          firms={firms}
          minZoom={9}
        />

        {selectedLL && (
          <EmojiMarker
            position={{ lat: selectedLL[0], lng: selectedLL[1] }}
            emoji="📍"
            title={selectedMeta?.title || "Selected"}
            draggable
            onDragEnd={(ll) =>
              setSelected(ll, { kind: "click", title: "Selected point" })
            }
          />
        )}

        {/* Quakes */}
        {quakes?.features?.map((f: any, i: number) => {
          const g = f.geometry;
          if (!g || g.type !== "Point") return null;
          const [lng, lat] = g.coordinates as [number, number];
          const p = f.properties || {};
          const m = p.mag ?? p.Magnitude ?? p.m ?? null;
          const place = p.place || p.title || "Earthquake";
          const src = p.url || p.detail || p.sources || "";
          return (
            <EmojiMarker
              key={`qk-${i}`}
              position={{ lat, lng }}
              emoji="💥"
              title={place}
              onClick={() =>
                setSelected([lat, lng], {
                  kind: "quake",
                  title: "Earthquake at " + place,
                  severity: m !== null ? `M${m}` : undefined,
                  sourceUrl: src || undefined,
                  confidence: 1,
                  emoji: "💥",
                  raw: p,
                })
              }
            />
          );
        })}

        {/* EONET */}
        {eonet?.features?.map((f: any, i: number) => {
          const g = f.geometry;
          if (!g || g.type !== "Point") return null;
          const [lng, lat] = g.coordinates as [number, number];
          const p = f.properties || {};
          const title = p.title || p.category || "Event";
          const emoji = eonetEmoji(p);
          const src = p.link || p.url || "";
          return (
            <EmojiMarker
              key={`eo-${i}`}
              position={{ lat, lng }}
              emoji={emoji}
              title={title}
              onClick={() =>
                setSelected([lat, lng], {
                  kind: "eonet",
                  title,
                  sourceUrl: src || undefined,
                  confidence: 1,
                  emoji,
                  raw: p,
                })
              }
            />
          );
        })}

        {/* User reports */}
        {reports.features.map((f, i) => {
          if (f.geometry?.type !== "Point") return null;
          const [lng, lat] = f.geometry.coordinates as [number, number];
          const p = f.properties || {};
          const iconName = p.icon || p.emoji || "info";
          const title = p.title || "User report";
          const desc = p.text || "";
          return (
            <AdvancedMarker
              key={`rp-${i}`}
              position={{ lat, lng }}
              title={title}
              zIndex={100}
              onClick={() =>
                setSelected([lat, lng], {
                  kind: "report",
                  title,
                  subtitle: desc,
                  severity: p.severity,
                  confidence: p.confidence,
                  category: p.category,
                  emoji: p.emoji,
                  raw: p,
                })
              }
            >
              <div className="bg-white rounded-full p-1 shadow-md border">
                <ReportIcon name={iconName} size={16} />
              </div>
            </AdvancedMarker>
          );
        })}
      </Map>
    </APIProvider>
  );
}
