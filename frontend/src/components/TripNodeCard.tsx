import { Clock3, MapPin } from "lucide-react";
import type { TripNode } from "../types/api";

type TripNodeCardProps = {
  node: TripNode;
  index: number;
  onAction: (node: TripNode) => void;
};

const typeLabel: Record<TripNode["type"], string> = {
  order: "待使用订单",
  interest: "兴趣节点",
  hotspot: "本地热点",
  nearby: "顺路 POI",
};

export default function TripNodeCard({ node, index, onAction }: TripNodeCardProps) {
  return (
    <article className="rounded-[28px] border border-slate-100 bg-white p-3 shadow-sm">
      <div className="flex gap-3">
        <div className="relative">
          <img className="h-24 w-24 rounded-2xl object-cover" src={node.imageUrl} alt={node.name} />
          <span className="absolute left-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-slate-950 text-xs font-bold text-white">
            {index + 1}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-600">
            {typeLabel[node.type]}
          </span>
          <h3 className="mt-2 line-clamp-1 text-base font-black text-slate-950">{node.title}</h3>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{node.reason}</p>
          <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-400">
            <Clock3 size={12} />
            {node.plannedStartTime}-{node.plannedEndTime}
          </p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-2">
        <div>
          <p className="text-sm font-bold text-slate-900">{node.name}</p>
          <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
            <MapPin size={12} />
            {node.distanceFromPreviousMeters > 0
              ? `距上一站 ${(node.distanceFromPreviousMeters / 1000).toFixed(1)}km · ${node.durationFromPreviousMinutes}分钟`
              : "从当前位置出发"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onAction(node)}
          className="rounded-full bg-slate-950 px-3 py-2 text-xs font-bold text-white"
        >
          {node.action.label}
        </button>
      </div>
      {node.availability.warnings.length ? (
        <p className="mt-2 rounded-2xl bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {node.availability.warnings.join("；")}
        </p>
      ) : null}
    </article>
  );
}
