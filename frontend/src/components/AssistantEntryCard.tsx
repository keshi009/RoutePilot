import { ArrowRight, Sparkles } from "lucide-react";

type AssistantEntryCardProps = {
  title: string;
  subtitle: string;
  copy?: string;
  eligibleOrderCount: number;
  onClick: () => void;
  onDismiss: () => void;
  onNotInterested: () => void;
};

export default function AssistantEntryCard({
  title,
  subtitle,
  copy,
  eligibleOrderCount,
  onClick,
  onDismiss,
  onNotInterested,
}: AssistantEntryCardProps) {
  return (
    <article className="relative w-full overflow-hidden rounded-[28px] bg-gradient-to-br from-[#2077ff] via-[#6d5dfc] to-[#f069b7] p-4 text-left text-white shadow-soft">
      <div className="absolute -right-10 -top-12 h-32 w-32 rounded-full bg-white/20" />
      <div className="absolute bottom-2 right-12 h-12 w-12 rounded-full bg-cyan-300/30" />
      <button
        type="button"
        aria-label="关闭 AI 订单助手入口"
        onClick={onDismiss}
        className="absolute right-3 top-3 z-10 rounded-full bg-white/15 px-2 py-1 text-[11px] font-bold text-white/85"
      >
        关闭
      </button>
      <button type="button" onClick={onClick} className="relative block w-full text-left">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-white/20">
            <Sparkles size={18} />
          </span>
          <div>
            <p className="text-sm font-bold">{title}</p>
            <p className="text-[11px] text-white/75">{subtitle}</p>
          </div>
        </div>
        <p className="mt-4 text-lg font-extrabold leading-snug">
          {copy ?? "你有待使用订单，我来帮你串成一条周末路线"}
        </p>
        <div className="mt-4 flex items-center justify-between">
          <span className="rounded-full bg-white/20 px-3 py-1 text-xs">{eligibleOrderCount} 张订单可安排</span>
          <span className="flex items-center gap-1 text-sm font-bold">
            开始规划 <ArrowRight size={16} />
          </span>
        </div>
      </button>
      <button
        type="button"
        onClick={onNotInterested}
        className="relative mt-3 text-xs font-semibold text-white/70 underline decoration-white/30 underline-offset-4"
      >
        不感兴趣，7 天内不再展示相似路线
      </button>
    </article>
  );
}
