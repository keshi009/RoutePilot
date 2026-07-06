"""打分引擎测试。

验证锚点订单、兴趣节点和整条路线的评分因子、惩罚项与可解释说明是否稳定。
"""

from app.agent import scoring
from app.agent.geo import haversine_meters
from app.mock import fixtures


def test_anchor_score_is_explainable():
    user = fixtures.get_user("u_mock_001")
    order = next(item for item in fixtures.ORDERS if item.order_id == "order_201")
    merchant = fixtures.get_merchant(order.merchant_id)

    score = scoring.score_anchor(order, merchant, user, usable_today=True, nearby_interest_count=3)

    assert score.total > 0
    assert "usability" in score.factors
    assert "queue" in score.penalties
    assert "今天可用" in score.notes


def test_poi_distance_score():
    user = fixtures.get_user("u_mock_001")
    interests = fixtures.get_interest_signals("u_mock_001")
    anchor = fixtures.get_merchant("merchant_nanshan_cantonese")
    poi = next(item for item in fixtures.POIS if item.poi_id == "poi_mixc_world_market")

    score = scoring.score_node(
        node_location=poi.location,
        tags=poi.recommended_tags + [poi.category],
        user=user,
        interests=interests,
        heat=poi.heat,
        rating=poi.rating,
        value=poi.avg_price,
        anchor_location=anchor.location,
    )

    assert haversine_meters(anchor.location, poi.location) > 0
    assert score.total > 0
    assert "interest_match" in score.factors


def test_route_score_penalizes_complexity():
    short = scoring.score_route(node_count=2, total_minutes=120, interest_node_count=1, anchor_usable=True)
    complex_route = scoring.score_route(node_count=5, total_minutes=120, interest_node_count=3, anchor_usable=True)

    assert complex_route.penalties["complexity"] > short.penalties["complexity"]
