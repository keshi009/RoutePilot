import { CalendarDays, MapPin } from "lucide-react";
import type { Order } from "../types/api";

type OrderCardProps = {
  order: Order;
};

export default function OrderCard({ order }: OrderCardProps) {
  const statusLabel = order.status === "unused" ? "待使用" : "不可规划";

  return (
    <article className="flex gap-3 rounded-3xl border border-slate-100 bg-white p-3 shadow-sm">
      <img className="h-24 w-24 rounded-2xl object-cover" src={order.imageUrl} alt={order.title} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-600">
            {statusLabel}
          </span>
          <span className="text-xs text-slate-400">¥{order.price}</span>
        </div>
        <h2 className="mt-2 line-clamp-2 text-sm font-bold text-slate-950">{order.title}</h2>
        <p className="mt-2 flex items-center gap-1 text-xs text-slate-500">
          <CalendarDays size={13} />
          有效期至 {order.validUntil}
        </p>
        <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
          <MapPin size={13} />
          {order.tags.slice(0, 2).join(" · ")}
        </p>
      </div>
    </article>
  );
}
