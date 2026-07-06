"""规划硬规则测试。

覆盖订单可用性、营业时间窗口和路线节点数等不可被 LLM 覆写的确定性规则。
"""

from app.agent import constraints
from app.mock import fixtures


def test_refunded_order_is_blocked():
    refunded = next(order for order in fixtures.ORDERS if order.status == "refunded")
    merchant = fixtures.get_merchant(refunded.merchant_id)
    hours = fixtures.get_business_hours(refunded.merchant_id)

    usable, warnings = constraints.is_order_usable_today(refunded, merchant, hours, weekday=5)

    assert usable is False
    assert warnings == ["订单状态为 refunded"]


def test_weekend_order_is_usable_when_windows_overlap():
    order = next(order for order in fixtures.ORDERS if order.order_id == "order_201")
    merchant = fixtures.get_merchant(order.merchant_id)
    hours = fixtures.get_business_hours(order.merchant_id)

    usable, warnings = constraints.is_order_usable_today(order, merchant, hours, weekday=5)

    assert usable is True
    assert warnings == []


def test_route_constraints_block_too_many_nodes():
    checks = constraints.validate_route(node_count=6, total_minutes=120)

    assert constraints.has_blocking(checks)
    assert any(check.rule_id == "node_count" and not check.passed for check in checks)
