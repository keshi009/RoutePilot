import { CheckCircle2, Loader2 } from "lucide-react";

const steps = [
  {
    title: "查看可用订单",
    description: "先确认哪些订单适合安排到最近周末。",
  },
  {
    title: "匹配周末时间",
    description: "避开不可用时间和太赶的消费节奏。",
  },
  {
    title: "查找附近地点",
    description: "结合你的兴趣，找出顺路可以去的地方。",
  },
  {
    title: "确定先去哪里",
    description: "优先安排更适合出行的一张订单。",
  },
  {
    title: "安排顺路路线",
    description: "尽量少绕路，同时保证不止一个可逛地点。",
  },
  {
    title: "计算路程时间",
    description: "确认总时长不会太长，也不会明显折返。",
  },
  {
    title: "整理推荐理由",
    description: "把路线说明整理成容易看的推荐卡片。",
  },
];

type PlanningStepsProps = {
  activeIndex: number;
};

export default function PlanningSteps({ activeIndex }: PlanningStepsProps) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const done = index < activeIndex;
        const active = index === activeIndex;
        return (
          <div key={step.title} className="flex items-center gap-3 rounded-2xl bg-white/80 p-3">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-full ${
                done ? "bg-emerald-100 text-emerald-600" : active ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? <CheckCircle2 size={18} /> : active ? <Loader2 className="animate-spin" size={18} /> : index + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-black text-slate-800">{step.title}</span>
              <span className="mt-0.5 block text-xs leading-5 text-slate-500">{step.description}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
