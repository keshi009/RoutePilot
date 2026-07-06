import type { RuleCheck, TripPlan } from "../types/api";

type Explainability = {
  routeAssessment?: string;
  filteredOrders?: Array<{
    orderId: string;
    title: string;
    merchantName: string;
    reasons: string[];
  }>;
};

type RuleExplainPanelProps = {
  plan: TripPlan;
};

function statusText(check: RuleCheck) {
  if (check.passed) {
    return "已通过";
  }
  return check.severity === "blocking" ? "阻断" : "提醒";
}

export default function RuleExplainPanel({ plan }: RuleExplainPanelProps) {
  const explainability = (plan.debug?.explainability ?? {}) as Explainability;
  const filteredOrders = explainability.filteredOrders ?? [];

  return (
    <section className="rounded-[28px] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-blue-600">推荐依据</p>
          <h2 className="mt-1 text-base font-black text-slate-950">为什么推荐这条路线</h2>
        </div>
      </div>

      {explainability.routeAssessment ? (
        <p className="mt-3 rounded-2xl bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-700">
          {explainability.routeAssessment}
        </p>
      ) : null}

      <div className="mt-4 grid grid-cols-1 gap-2">
        {plan.ruleChecks.map((check) => (
          <div key={`${check.ruleId}-${check.affectedEntityId ?? "route"}`} className="flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-2">
            <span className="text-xs font-semibold text-slate-700">{check.message}</span>
            <span className={check.passed ? "text-xs font-bold text-emerald-600" : "text-xs font-bold text-amber-600"}>
              {statusText(check)}
            </span>
          </div>
        ))}
      </div>

      {filteredOrders.length ? (
        <div className="mt-4">
          <p className="text-xs font-bold text-slate-500">其他订单暂不推荐</p>
          <div className="mt-2 space-y-2">
            {filteredOrders.slice(0, 4).map((order) => (
              <div key={order.orderId} className="rounded-2xl border border-slate-100 px-3 py-2">
                <p className="text-xs font-bold text-slate-800">{order.title}</p>
                <p className="mt-1 text-[11px] leading-5 text-slate-500">{order.reasons.join("；")}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
