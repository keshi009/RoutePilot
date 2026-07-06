import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAssistantEntry, fetchOrders, trackEvent } from "../api/client";
import AssistantEntryCard from "../components/AssistantEntryCard";
import EmptyState from "../components/EmptyState";
import MobileShell from "../components/MobileShell";
import OrderCard from "../components/OrderCard";
import type { AssistantEntry, Order } from "../types/api";

const ENTRY_DISMISS_KEY = "routepilot_entry_dismiss_until";
const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

function isEntryLocallySuppressed() {
  try {
    const dismissedUntil = Number(window.localStorage.getItem(ENTRY_DISMISS_KEY) ?? "0");
    return dismissedUntil > Date.now();
  } catch {
    return false;
  }
}

export default function OrderListPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [entry, setEntry] = useState<AssistantEntry | null>(null);
  const [entryHidden, setEntryHidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchOrders(), fetchAssistantEntry()])
      .then(([orderData, entryData]) => {
        setOrders(orderData);
        setEntry(entryData);
        if (entryData.visible && !isEntryLocallySuppressed()) {
            setEntryHidden(false);
        } else {
          setEntryHidden(true);
        }
        void trackEvent({ eventName: "order_list_exposure", userId: "u_mock_001" });
      })
      .catch((fetchError: Error) => {
        setError(fetchError.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const unusedOrders = orders.filter((order) => order.status === "unused");
  const showEntry = Boolean(entry?.visible && !entryHidden);

  return (
    <MobileShell title="订单" subtitle="看看哪些订单适合周末去用">
      <div className="space-y-4 bg-[#f6f8fc] px-4 pb-8 pt-2">
        {showEntry && entry ? (
          <AssistantEntryCard
            title={entry.title}
            subtitle={entry.subtitle}
            copy={entry.copy}
            eligibleOrderCount={entry.eligibleOrderCount}
            onClick={() => {
              void trackEvent({
                eventName: "assistant_entry_click",
                userId: "u_mock_001",
                payload: { candidateOrderIds: entry.candidateOrderIds, source: entry.entryCopySource },
              });
              navigate("/planning");
            }}
            onDismiss={() => {
              setEntryHidden(true);
              void trackEvent({ eventName: "assistant_entry_close", userId: "u_mock_001" });
            }}
            onNotInterested={() => {
              try {
                window.localStorage.setItem(ENTRY_DISMISS_KEY, String(Date.now() + SEVEN_DAYS_MS));
              } catch {
                // Ignore storage failures; UI state still hides the entry.
              }
              setEntryHidden(true);
              void trackEvent({ eventName: "assistant_entry_not_interested", userId: "u_mock_001" });
            }}
          />
        ) : null}

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-black text-slate-950">待使用订单</h2>
            <span className="text-xs text-slate-400">最近周末可安排</span>
          </div>
          {error ? (
            <EmptyState title="订单读取失败" description={error} />
          ) : loading ? (
            <EmptyState title="正在读取订单" description="正在查看你的待使用订单和有效期。" />
          ) : unusedOrders.length ? (
            <div className="space-y-3">
              {unusedOrders.map((order) => (
                <OrderCard key={order.orderId} order={order} />
              ))}
            </div>
          ) : (
            <EmptyState title="暂无待使用订单" description="有适合安排的订单时，会再为你推荐路线。" />
          )}
        </div>
      </div>
    </MobileShell>
  );
}
