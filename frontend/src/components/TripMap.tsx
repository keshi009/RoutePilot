import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import type { TripPlan } from "../types/api";

type TripMapProps = {
  plan: TripPlan;
};

function markerIcon(index: number, type: string, name: string, reason: string) {
  const color = type === "order" ? "#1d4ed8" : "#ec4899";
  const label = name.length > 12 ? `${name.slice(0, 12)}...` : name;
  const desc = reason.length > 14 ? `${reason.slice(0, 14)}...` : reason;
  return L.divIcon({
    className: "",
    html: `<div style="
      display:flex;align-items:center;gap:5px;min-width:128px;max-width:154px;
      padding:4px 7px 4px 4px;border-radius:999px;background:rgba(255,255,255,.94);
      border:1px solid rgba(15,23,42,.08);box-shadow:0 8px 24px rgba(15,23,42,.22);
      font-family:-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;
    ">
      <span style="
        flex:0 0 auto;width:24px;height:24px;border-radius:999px;background:${color};
        color:white;display:flex;align-items:center;justify-content:center;
        font-size:12px;font-weight:900;border:2px solid white;
      ">${index + 1}</span>
      <span style="display:flex;flex-direction:column;line-height:1.15;min-width:0;">
        <strong style="font-size:11px;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${label}</strong>
        <em style="font-style:normal;font-size:9px;color:#ec4899;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${desc}</em>
      </span>
    </div>`,
    iconSize: [148, 34],
    iconAnchor: [16, 17],
  });
}

const userIcon = L.divIcon({
  className: "",
  html: `<div style="
    width:78px;padding:5px 8px;border-radius:999px;background:#0f172a;color:white;
    border:2px solid white;box-shadow:0 8px 22px rgba(15,23,42,.26);
    font-family:-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;
    font-size:11px;font-weight:900;text-align:center;
  ">你在这里</div>`,
  iconSize: [78, 28],
  iconAnchor: [39, 14],
});

export default function TripMap({ plan }: TripMapProps) {
  const center = plan.userLocation ?? plan.nodes[0]?.location ?? { lat: 39.9924, lng: 116.4752 };
  const line = plan.route.polyline.map((point) => [point.lat, point.lng] as [number, number]);

  return (
    <section className="h-[300px] overflow-hidden rounded-b-[34px] bg-slate-200">
      <MapContainer center={[center.lat, center.lng]} zoom={15} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {line.length > 1 ? <Polyline positions={line} pathOptions={{ color: "#2563eb", weight: 5, opacity: 0.8 }} /> : null}
        <Marker position={[plan.userLocation.lat, plan.userLocation.lng]} icon={userIcon}>
          <Popup>你的位置</Popup>
        </Marker>
        {plan.nodes.map((node, index) => (
          <Marker
            key={node.nodeId}
            position={[node.location.lat, node.location.lng]}
            icon={markerIcon(index, node.type, node.name, node.reason)}
          >
            <Popup>
              <strong>{node.name}</strong>
              <br />
              {node.reason}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </section>
  );
}
