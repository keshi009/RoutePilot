import { useEffect, useRef, useState } from "react";
import { createTripPlanStream, executeTripAction, trackEvent } from "../api/client";
import ActionToast from "../components/ActionToast";
import EmptyState from "../components/EmptyState";
import MobileShell from "../components/MobileShell";
import TripMap from "../components/TripMap";
import TripNodeCard from "../components/TripNodeCard";
import TripSummaryCard from "../components/TripSummaryCard";
import type { PlanningFailure, PlanningProgressEvent, TripNode, TripPlan } from "../types/api";

export default function PlanningPage() {
  const [failure, setFailure] = useState<PlanningFailure | null>(null);
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [showFullPlan, setShowFullPlan] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [progressEvents, setProgressEvents] = useState<PlanningProgressEvent[]>([
    { progressTitle: "正在准备行程", detailText: "马上开始查看可用订单和附近地点" },
  ]);
  const hasStartedPlanningRef = useRef(false);

  useEffect(() => {
    if (hasStartedPlanningRef.current) {
      return;
    }
    hasStartedPlanningRef.current = true;

    void trackEvent({ eventName: "planning_start", userId: "u_mock_001" });

    createTripPlanStream((event) => {
      const normalized = {
        ...event,
        progressTitle: event.progressTitle ?? "正在规划",
      };
      setProgressEvents((events) => {
        if (normalized.sequence && events[0]?.sequence === normalized.sequence) {
          return events;
        }
        return [normalized];
      });
    })
      .then((result) => {
        if (result.status === "success") {
          void trackEvent({ eventName: "planning_success", userId: "u_mock_001", planId: result.planId });
          setProgressEvents([{ progressTitle: "规划完成", detailText: "正在渲染地图和推荐卡片" }]);
          setPlan(result);
        } else {
          void trackEvent({
            eventName: "planning_failed",
            userId: "u_mock_001",
            payload: { failureCode: result.failureCode },
          });
          setFailure(result);
        }
      })
      .catch((error: Error) => {
        setFailure({
          status: "failed",
          failureCode: "NETWORK_ERROR",
          message: error.message,
          ruleChecks: [],
        });
      });
  }, []);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  };

  const handleNodeAction = (node: TripNode) => {
    if (!plan) {
      return;
    }
    executeTripAction({
      planId: plan.planId,
      nodeId: node.nodeId,
      actionType: node.action.type,
      entityId: node.entityId,
    })
      .then((result) => showToast(result.message))
      .catch(() => showToast(node.action.disabledReason ?? "动作服务暂不可用，请稍后再试"));
  };

  const latestProgress = progressEvents[progressEvents.length - 1];
  const anchorNode = plan?.nodes.find((node) => node.type === "order");

  return (
    <MobileShell title="AI 订单助手" subtitle="帮你安排最近周末">
      {plan ? <TripMap plan={plan} /> : null}
      <div className="space-y-5 bg-[#f6f8fc] px-4 pb-8 pt-4">
        <section className="rounded-[30px] bg-gradient-to-br from-slate-950 to-blue-950 p-5 text-white shadow-soft">
          <p className="text-xs font-semibold text-cyan-200">{plan ? "已生成推荐" : "正在为你安排"}</p>
          <h1 className="mt-2 text-2xl font-black leading-tight">
            {plan ? "已为你生成最近周末行程" : "正在根据最近周末和待使用订单规划"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-white/70">
            {plan
              ? "已结合你的位置、待使用订单和附近地点，生成一条更顺路的周末安排。"
              : "会先确认你的位置，再查看可用订单和附近地点。"}
          </p>
        </section>

        {failure ? (
          <EmptyState
            title="暂时无法生成行程"
            description={`${failure.message}（${failure.failureCode}）`}
            actionLabel="重新规划"
            onAction={() => window.location.reload()}
          />
        ) : plan ? (
          <>
            <TripSummaryCard plan={plan} />
            {!showFullPlan ? (
              <section className="overflow-hidden rounded-[30px] bg-white shadow-soft">
                <div className="bg-gradient-to-br from-blue-600 via-indigo-600 to-pink-500 p-5 text-white">
                  <p className="text-xs font-bold text-white/75">AI 已完成规划</p>
                  <h2 className="mt-2 text-2xl font-black leading-tight">{plan.summary.title}</h2>
                  <p className="mt-3 text-sm leading-6 text-white/85">{plan.summary.text}</p>
                </div>
                <div className="space-y-4 p-4">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-lg font-black text-slate-950">{plan.nodes.length}</p>
                      <p className="text-[11px] text-slate-500">行程节点</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-lg font-black text-slate-950">{(plan.route.totalDistanceMeters / 1000).toFixed(1)}km</p>
                      <p className="text-[11px] text-slate-500">路线距离</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-lg font-black text-slate-950">{plan.route.totalDurationMinutes}m</p>
                      <p className="text-[11px] text-slate-500">预计耗时</p>
                    </div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-3">
                    <p className="text-xs font-bold text-blue-600">为什么推荐这条路线</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      主锚点订单为 {anchorNode?.name ?? "待使用订单"}，最近周末可用且门店营业；附近组合了你感兴趣的
                      {plan.nodes.filter((node) => node.type !== "order").map((node) => node.name).join("、")}，整体不超过 5 小时。
                    </p>
                  </div>
                  <div className="space-y-2">
                    {plan.nodes.slice(0, 3).map((node, index) => (
                      <div key={node.nodeId} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-bold text-slate-900">{node.name}</p>
                          <p className="truncate text-xs text-slate-500">{node.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setShowFullPlan(true);
                      void trackEvent({ eventName: "view_full_trip_plan_click", userId: "u_mock_001", planId: plan.planId });
                    }}
                    className="flex w-full items-center justify-center rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white"
                  >
                    查看完整行程规划
                  </button>
                </div>
              </section>
            ) : (
              <>
                <section className="rounded-[28px] bg-white p-4 shadow-sm">
                  <p className="text-xs font-bold text-blue-600">继续调整行程</p>
                  <button
                    type="button"
                    onClick={() => showToast("继续调整行程的多轮编排暂未接入，本期先记录入口点击")}
                    className="mt-3 w-full rounded-2xl bg-slate-100 px-4 py-3 text-left text-sm font-semibold text-slate-600"
                  >
                    想换成更轻松、少走路或更适合亲子的路线？
                  </button>
                </section>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-black text-slate-950">完整行程规划</h2>
                    <span className="text-xs text-slate-400">{plan.nodes.length} 站路线</span>
                  </div>
                  {plan.nodes.map((node, index) => (
                    <TripNodeCard key={node.nodeId} node={node} index={index} onAction={handleNodeAction} />
                  ))}
                </div>
              </>
            )}
          </>
        ) : (
          <section className="rounded-[22px] bg-white p-3 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-blue-50">
                <div className="h-6 w-6 animate-spin rounded-full border-[3px] border-blue-100 border-t-blue-600" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="truncate text-base font-black text-slate-950">{latestProgress?.progressTitle ?? "AI 正在规划中"}</h2>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                  {latestProgress?.detailText || "正在整理路线，完成后会立即展示结果。"}
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
      <ActionToast message={toast} />
    </MobileShell>
  );
}
