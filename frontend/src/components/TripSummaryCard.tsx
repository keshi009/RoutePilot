import { Sparkles } from "lucide-react";
import type { TripPlan } from "../types/api";

type TripSummaryCardProps = {
  plan: TripPlan;
};

export default function TripSummaryCard({ plan }: TripSummaryCardProps) {
  return (
    <section className="rounded-[28px] bg-slate-950 p-4 text-white shadow-soft">
      <div className="flex items-center gap-2 text-cyan-200">
        <Sparkles size={16} />
        <span className="text-xs font-semibold">AI 行程概述 · {plan.targetDateLabel}</span>
      </div>
      <h2 className="mt-3 text-xl font-black">{plan.summary.title}</h2>
      <p className="mt-2 text-sm leading-6 text-white/80">{plan.summary.text}</p>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-2xl bg-white/10 p-2">
          <p className="text-lg font-bold">{plan.nodes.length}</p>
          <p className="text-[11px] text-white/60">节点</p>
        </div>
        <div className="rounded-2xl bg-white/10 p-2">
          <p className="text-lg font-bold">{(plan.route.totalDistanceMeters / 1000).toFixed(1)}km</p>
          <p className="text-[11px] text-white/60">路线</p>
        </div>
        <div className="rounded-2xl bg-white/10 p-2">
          <p className="text-lg font-bold">{plan.route.totalDurationMinutes}m</p>
          <p className="text-[11px] text-white/60">总时长</p>
        </div>
      </div>
    </section>
  );
}
