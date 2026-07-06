"""固定 Mock 数据 + scenario 感知的访问函数（深圳单用户样例）。

数据来自旧 adapters/mock_trip_data.py，迁移为返回 v2 契约对象的纯函数。
未来把这些函数替换为公司内部 RPC 调用即可，上层无感。

scenario 分支用于测试与演示：
- no_orders          : 无待使用订单 -> 触发 no_eligible_orders
- weekend_unavailable: 仅剩周末不可用订单 -> 触发 no_usable_time
- merchant_closed    : 订单对应商家周末闭店
- route_too_long     : 兴趣候选只剩超远 POI -> 触发路线约束失败
- no_poi             : 无正常 POI
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional
from urllib.parse import quote

from app.contracts import (
    BusinessDay,
    BusinessHours,
    InterestSignal,
    Location,
    Merchant,
    Order,
    Poi,
    TimeWindow,
    UserProfile,
    WeatherSnapshot,
)


def image_url(prompt: str, image_size: str = "landscape_4_3") -> str:
    """生成图片 URL（走批准的文生图端点）。"""

    encoded = quote(prompt)
    return (
        "https://copilot-cn.bytedance.net/api/ide/v1/text_to_image"
        f"?prompt={encoded}&image_size={image_size}"
    )


USER = UserProfile(
    userId="u_mock_001",
    displayName="周以安",
    city="深圳",
    currentLocation=Location(lat=22.5333, lng=113.9468),
    weekendPreferredWindow=TimeWindow(start="10:30", end="17:00"),
    preferenceTags=["粤菜", "咖啡", "展览", "海边散步", "书店", "亲子", "南山", "轻松周末"],
)


INTERESTS: List[InterestSignal] = [
    InterestSignal(signalId="interest_sz_001", source="favorite", label="深圳湾海边散步", weight=0.94,
                   relatedCategories=["公园", "海边", "亲子", "轻松"]),
    InterestSignal(signalId="interest_sz_002", source="browse", label="南山博物馆周末展", weight=0.86,
                   relatedCategories=["展览", "博物馆", "文化"]),
    InterestSignal(signalId="interest_sz_003", source="purchase", label="粤菜点心", weight=0.8,
                   relatedCategories=["美食", "粤菜", "午餐"]),
    InterestSignal(signalId="interest_sz_004", source="search", label="万象天地咖啡书店", weight=0.72,
                   relatedCategories=["咖啡", "书店", "商圈"]),
]


def _week(open_close: List[tuple], closed_days: Optional[set] = None) -> List[BusinessDay]:
    closed_days = closed_days or set()
    days = []
    for wd in range(7):
        if wd in closed_days:
            days.append(BusinessDay(weekday=wd, openTime="00:00", closeTime="00:00", isClosed=True))
        else:
            o, c = open_close[wd]
            days.append(BusinessDay(weekday=wd, openTime=o, closeTime=c))
    return days


BUSINESS_HOURS: Dict[str, BusinessHours] = {
    "hours_nanshan_cantonese": BusinessHours(
        merchantId="merchant_nanshan_cantonese",
        weekly=_week([("11:00", "21:30")] * 4 + [("11:00", "22:00"), ("10:30", "22:00"), ("10:30", "21:30")]),
        notes=["周末午市可用，12 点后可能排队。"],
    ),
    "hours_bay_cafe": BusinessHours(
        merchantId="merchant_bay_cafe",
        weekly=_week([("08:30", "21:00")] * 4 + [("08:30", "22:00"), ("09:00", "22:00"), ("09:00", "21:30")]),
        notes=["上午和下午均可使用，适合作为轻路线起点。"],
    ),
    "hours_shekou_brunch": BusinessHours(
        merchantId="merchant_shekou_brunch",
        weekly=_week([("10:00", "20:30")] * 4 + [("10:00", "21:30"), ("09:30", "21:30"), ("09:30", "21:00")]),
        notes=["蛇口区域距离略远，适合半日路线备选。"],
    ),
    "hours_oct_dessert": BusinessHours(
        merchantId="merchant_oct_dessert",
        weekly=_week([("11:00", "22:00")] * 4 + [("11:00", "22:30"), ("10:30", "22:30"), ("10:30", "22:00")]),
        notes=["适合展览后作为下午茶补充节点。"],
    ),
    "hours_evening_hotpot": BusinessHours(
        merchantId="merchant_evening_hotpot",
        weekly=_week([("17:00", "23:30")] * 4 + [("17:00", "23:59"), ("16:30", "23:59"), ("16:30", "23:30")]),
        notes=["晚市券，不适合当前午后主窗口。"],
    ),
    "hours_weekday_salad": BusinessHours(
        merchantId="merchant_weekday_salad",
        weekly=_week([("10:00", "19:00")] * 5 + [("00:00", "00:00"), ("00:00", "00:00")], closed_days={5, 6}),
        notes=["周末闭店，用于过滤验证。"],
    ),
}


MERCHANTS: Dict[str, Merchant] = {
    "merchant_nanshan_cantonese": Merchant(
        merchantId="merchant_nanshan_cantonese", name="南山拾味·粤菜小馆（科技园店）", category="美食",
        address="深圳市南山区科兴科学园 B 座 2 层", location=Location(lat=22.5382, lng=113.9461),
        rating=4.7, avgPrice=138, status="normal", reservationRequired=False, reservationRisk=15, queueRisk=46,
        imageUrl=image_url("realistic Cantonese lunch restaurant in Shenzhen Nanshan warm light"),
        businessHoursId="hours_nanshan_cantonese"),
    "merchant_bay_cafe": Merchant(
        merchantId="merchant_bay_cafe", name="M Stand Coffee（深圳湾万象城店）", category="咖啡",
        address="深圳市南山区深圳湾万象城 L1", location=Location(lat=22.5242, lng=113.9454),
        rating=4.6, avgPrice=46, status="normal", reservationRequired=False, reservationRisk=0, queueRisk=26,
        imageUrl=image_url("modern specialty coffee shop in Shenzhen Bay shopping mall realistic"),
        businessHoursId="hours_bay_cafe"),
    "merchant_shekou_brunch": Merchant(
        merchantId="merchant_shekou_brunch", name="海上世界 Brunch Lab", category="西式简餐",
        address="深圳市南山区海上世界文化艺术中心旁", location=Location(lat=22.4796, lng=113.9198),
        rating=4.5, avgPrice=128, status="normal", reservationRequired=True, reservationRisk=62, queueRisk=24,
        imageUrl=image_url("brunch cafe near Sea World Shenzhen realistic daylight"),
        businessHoursId="hours_shekou_brunch"),
    "merchant_oct_dessert": Merchant(
        merchantId="merchant_oct_dessert", name="OCT Loft 甜品研究所", category="甜品",
        address="深圳市南山区华侨城创意文化园北区", location=Location(lat=22.5401, lng=113.9862),
        rating=4.5, avgPrice=58, status="normal", reservationRequired=False, reservationRisk=0, queueRisk=34,
        imageUrl=image_url("dessert cafe in OCT Loft Shenzhen creative park realistic"),
        businessHoursId="hours_oct_dessert"),
    "merchant_evening_hotpot": Merchant(
        merchantId="merchant_evening_hotpot", name="前海潮牛火锅（晚市店）", category="美食",
        address="深圳市南山区前海卓悦 INTOWN 4 层", location=Location(lat=22.5271, lng=113.9026),
        rating=4.4, avgPrice=168, status="normal", reservationRequired=False, reservationRisk=25, queueRisk=78,
        imageUrl=image_url("busy Shenzhen beef hotpot restaurant evening realistic"),
        businessHoursId="hours_evening_hotpot"),
    "merchant_weekday_salad": Merchant(
        merchantId="merchant_weekday_salad", name="周末不营业的科技园轻食店", category="轻食",
        address="深圳市南山区粤海街道软件产业基地", location=Location(lat=22.5298, lng=113.9508),
        rating=4.2, avgPrice=39, status="normal", reservationRequired=False, reservationRisk=0, queueRisk=8,
        imageUrl=image_url("closed healthy salad cafe in Shenzhen tech park weekend realistic"),
        businessHoursId="hours_weekday_salad"),
}


ORDERS: List[Order] = [
    Order(orderId="order_201", userId="u_mock_001", merchantId="merchant_nanshan_cantonese",
          title="南山拾味粤菜双人午市套餐", category="美食", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4, 5, 6],
          usableTimeWindows=[TimeWindow(start="11:00", end="14:30"), TimeWindow(start="17:00", end="20:30")],
          price=188, value=288, needsReservation=False, tags=["粤菜", "午餐", "双人餐", "科技园"],
          imageUrl=MERCHANTS["merchant_nanshan_cantonese"].image_url),
    Order(orderId="order_202", userId="u_mock_001", merchantId="merchant_bay_cafe",
          title="M Stand 深圳湾双杯咖啡券", category="咖啡", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4, 5, 6],
          usableTimeWindows=[TimeWindow(start="10:00", end="18:30")],
          price=66, value=98, needsReservation=False, tags=["咖啡", "深圳湾", "下午茶", "轻松"],
          imageUrl=MERCHANTS["merchant_bay_cafe"].image_url),
    Order(orderId="order_203", userId="u_mock_001", merchantId="merchant_shekou_brunch",
          title="海上世界 Brunch 双人券", category="西式简餐", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4, 5, 6],
          usableTimeWindows=[TimeWindow(start="10:30", end="16:00")],
          price=168, value=238, needsReservation=True, tags=["Brunch", "蛇口", "需要预约", "半日路线"],
          imageUrl=MERCHANTS["merchant_shekou_brunch"].image_url),
    Order(orderId="order_204", userId="u_mock_001", merchantId="merchant_oct_dessert",
          title="OCT Loft 甜品下午茶券", category="甜品", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4, 5, 6],
          usableTimeWindows=[TimeWindow(start="12:00", end="18:30")],
          price=88, value=128, needsReservation=False, tags=["甜品", "华侨城", "展览后", "下午茶"],
          imageUrl=MERCHANTS["merchant_oct_dessert"].image_url),
    Order(orderId="order_205", userId="u_mock_001", merchantId="merchant_evening_hotpot",
          title="前海潮牛火锅双人晚市券", category="美食", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4, 5, 6],
          usableTimeWindows=[TimeWindow(start="17:30", end="22:30")],
          price=198, value=298, needsReservation=False, tags=["晚餐", "火锅", "排队风险", "当前窗口过滤"],
          imageUrl=MERCHANTS["merchant_evening_hotpot"].image_url),
    Order(orderId="order_206", userId="u_mock_001", merchantId="merchant_weekday_salad",
          title="科技园轻食工作日午餐券", category="轻食", status="unused",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[0, 1, 2, 3, 4],
          usableTimeWindows=[TimeWindow(start="10:30", end="14:00")],
          price=42, value=58, needsReservation=False, tags=["工作日", "周末不可用", "过滤验证"],
          imageUrl=MERCHANTS["merchant_weekday_salad"].image_url),
    Order(orderId="order_207", userId="u_mock_001", merchantId="merchant_nanshan_cantonese",
          title="已退款的粤菜点心券", category="美食", status="refunded",
          validFrom="2026-01-01", validUntil="2026-12-31", usableWeekdays=[5, 6],
          usableTimeWindows=[TimeWindow(start="11:00", end="14:30")],
          price=79, value=118, needsReservation=False, tags=["退款", "过滤验证"],
          imageUrl=MERCHANTS["merchant_nanshan_cantonese"].image_url),
]


POIS: List[Poi] = [
    Poi(poiId="poi_nanshan_museum", name="南山博物馆周末展", category="博物馆", source="interest",
        location=Location(lat=22.5337, lng=113.9298), rating=4.8, heat=92, avgPrice=0, status="normal",
        recommendedTags=["展览", "文化", "亲子", "周末"], actionType="view", openTime="10:00", closeTime="18:00",
        imageUrl=image_url("Shenzhen Nanshan Museum weekend exhibition realistic visitors")),
    Poi(poiId="poi_shenzhen_bay_park", name="深圳湾公园海边步道", category="公园", source="nearby",
        location=Location(lat=22.5159, lng=113.9449), rating=4.9, heat=96, avgPrice=0, status="normal",
        recommendedTags=["海边", "散步", "亲子", "轻松"], actionType="browse", openTime="06:00", closeTime="22:00",
        imageUrl=image_url("Shenzhen Bay Park seaside promenade weekend realistic")),
    Poi(poiId="poi_mixc_world_market", name="万象天地周末生活市集", category="商圈", source="hotspot",
        location=Location(lat=22.5436, lng=113.9524), rating=4.6, heat=85, avgPrice=0, status="normal",
        recommendedTags=["商圈", "咖啡", "市集", "少绕路"], actionType="browse", openTime="11:00", closeTime="21:00",
        imageUrl=image_url("Shenzhen MixC World weekend lifestyle market realistic")),
    Poi(poiId="poi_oct_loft_gallery", name="华侨城创意园设计展", category="展览", source="interest",
        location=Location(lat=22.5407, lng=113.9868), rating=4.7, heat=84, avgPrice=30, status="normal",
        recommendedTags=["设计", "展览", "书店", "下午茶"], actionType="view", openTime="10:00", closeTime="19:00",
        imageUrl=image_url("OCT Loft Shenzhen creative design exhibition realistic")),
    Poi(poiId="poi_bay_bookstore", name="深圳湾睿印书店", category="书店", source="nearby",
        location=Location(lat=22.5267, lng=113.9422), rating=4.7, heat=78, avgPrice=55, status="normal",
        recommendedTags=["书店", "咖啡", "雨天备选"], actionType="view", openTime="10:00", closeTime="22:00",
        imageUrl=image_url("quiet bookstore cafe in Shenzhen Bay shopping district realistic")),
    Poi(poiId="poi_sea_world_art_center", name="海上世界文化艺术中心", category="展览", source="hotspot",
        location=Location(lat=22.4792, lng=113.9189), rating=4.8, heat=89, avgPrice=68, status="normal",
        recommendedTags=["蛇口", "展览", "海边", "距离较远"], actionType="purchase_placeholder", openTime="10:00", closeTime="21:00",
        imageUrl=image_url("Sea World Culture and Arts Center Shenzhen realistic architecture")),
    Poi(poiId="poi_closed_gallery", name="临时闭馆的南头艺术空间", category="展览", source="interest",
        location=Location(lat=22.5411, lng=113.9308), rating=4.3, heat=62, avgPrice=25, status="closed",
        recommendedTags=["闭馆过滤", "异常验证"], actionType="view", openTime="10:00", closeTime="18:00",
        imageUrl=image_url("closed contemporary art gallery entrance Shenzhen realistic")),
    Poi(poiId="poi_far_dapeng", name="大鹏所城海岸线", category="公园", source="hotspot",
        location=Location(lat=22.5968, lng=114.4744), rating=4.7, heat=91, avgPrice=0, status="normal",
        recommendedTags=["距离过远过滤", "海边"], actionType="browse", openTime="09:00", closeTime="20:00",
        imageUrl=image_url("Dapeng coastal town Shenzhen seaside realistic")),
]


WEATHER: List[WeatherSnapshot] = [
    WeatherSnapshot(date="nearest_weekend", condition="多云间晴", temperature="27-32°C", outdoorScore=76,
                    tips=["适合短距离步行和室内外结合路线", "午后海边注意防晒补水"]),
]


def _copy(item):
    return item.model_copy(deep=True)


def _copy_list(items):
    return [_copy(x) for x in items]


# ---- 对外访问函数（未来替换为 RPC 调用） ----

def get_user(user_id: str) -> UserProfile:
    return _copy(USER)


def get_interest_signals(user_id: str) -> List[InterestSignal]:
    return _copy_list(INTERESTS)


def get_unused_orders(user_id: str, scenario: Optional[str] = None) -> List[Order]:
    """返回待使用订单（status=unused）。scenario 控制测试分支。"""

    if scenario == "no_orders":
        return []
    if scenario == "weekend_unavailable":
        return [o for o in _copy_list(ORDERS) if o.order_id == "order_206"]
    if scenario == "merchant_closed":
        closed = _copy(ORDERS[0])
        closed.order_id = "order_closed_shenzhen"
        closed.merchant_id = "merchant_weekday_salad"
        closed.usable_weekdays = [5, 6]
        return [closed]
    return [o for o in _copy_list(ORDERS) if o.user_id == user_id and o.status == "unused"]


def get_merchant(merchant_id: str) -> Optional[Merchant]:
    m = MERCHANTS.get(merchant_id)
    return _copy(m) if m else None


def get_business_hours(merchant_id: str) -> Optional[BusinessHours]:
    m = MERCHANTS.get(merchant_id)
    if not m:
        return None
    bh = BUSINESS_HOURS.get(m.business_hours_id)
    return _copy(bh) if bh else None


def get_nearby_pois(lat: float, lng: float, radius_m: int = 5000, scenario: Optional[str] = None) -> List[Poi]:
    """返回周边 POI（含兴趣/热点/nearby）。scenario 控制测试分支。

    半径过滤由上层 recall 节点结合 haversine 做；这里 mock 直接返回候选池。
    """

    if scenario == "no_poi":
        return [p for p in _copy_list(POIS) if p.status != "normal"]
    if scenario == "route_too_long":
        return [p for p in _copy_list(POIS) if p.poi_id == "poi_far_dapeng"]
    return _copy_list(POIS)


def get_local_hotspots(city: str, scenario: Optional[str] = None) -> List[Poi]:
    return [p for p in get_nearby_pois(0, 0, scenario=scenario) if p.source == "hotspot"]


def get_weather(city: str, date_key: str = "nearest_weekend") -> Optional[WeatherSnapshot]:
    for item in WEATHER:
        if item.date == date_key:
            return _copy(item)
    return _copy(WEATHER[0]) if WEATHER else None
