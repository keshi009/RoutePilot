"""External mock trip-data API.

This service simulates APIs owned by other teams: order center, merchant center,
POI/search, user profile, and location. It returns fixed data but is called over
HTTP by RoutePilot, so the backend integration path is production-like.
"""

import copy
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query


DATA_PATH = Path(__file__).with_name("mock_dataset.json")
app = FastAPI(title="RoutePilot External Mock Trip Data API", version="0.1.0")


def _dataset() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _copy(value):
    return copy.deepcopy(value)


def _orders_for_scenario(dataset: dict, user_id: str, scenario: Optional[str]) -> List[dict]:
    orders = [order for order in dataset["orders"] if order["userId"] == user_id]
    if scenario == "no_orders":
        return []
    if scenario == "weekend_unavailable":
        return [order for order in orders if order["orderId"] == "order_206"]
    if scenario == "merchant_closed":
        closed_order = _copy(next(order for order in orders if order["orderId"] == "order_201"))
        closed_order["orderId"] = "order_closed_shenzhen"
        closed_order["merchantId"] = "merchant_weekday_salad"
        closed_order["usableWeekdays"] = [5, 6]
        return [closed_order]
    return orders


def _pois_for_scenario(dataset: dict, scenario: Optional[str]) -> List[dict]:
    pois = dataset["pois"]
    if scenario == "no_poi":
        return [poi for poi in pois if poi["status"] != "normal"]
    if scenario == "route_too_long":
        return [poi for poi in pois if poi["poiId"] == "poi_far_dapeng"]
    return pois


@app.get("/health")
def health():
    return {"ok": True, "service": "external-trip-data-mock"}


@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    user = _dataset()["users"].get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _copy(user)


@app.get("/api/users/{user_id}/location")
def get_user_location(user_id: str):
    user = get_user(user_id)
    return {
        "userId": user["userId"],
        "city": user["city"],
        "source": "mock",
        "accuracyMeters": 80,
        "location": user["currentLocation"],
    }


@app.get("/api/users/{user_id}/interests")
def list_interests(user_id: str):
    dataset = _dataset()
    if user_id not in dataset["users"]:
        raise HTTPException(status_code=404, detail="User not found")
    return _copy(dataset["interests"].get(user_id, []))


@app.get("/api/orders")
def list_orders(user_id: str = Query("u_mock_001", alias="userId"), scenario: Optional[str] = Query(None)):
    return _copy(_orders_for_scenario(_dataset(), user_id, scenario))


@app.get("/api/orders/{order_id}")
def get_order(order_id: str, scenario: Optional[str] = Query(None)):
    for order in _orders_for_scenario(_dataset(), "u_mock_001", scenario):
        if order["orderId"] == order_id:
            return _copy(order)
    raise HTTPException(status_code=404, detail="Order not found")


@app.get("/api/merchants")
def list_merchants(merchant_ids: Optional[List[str]] = Query(None, alias="merchantIds")):
    merchants = _dataset()["merchants"]
    ids = merchant_ids or list(merchants.keys())
    return _copy({merchant_id: merchants[merchant_id] for merchant_id in ids if merchant_id in merchants})


@app.get("/api/merchants/{merchant_id}")
def get_merchant(merchant_id: str):
    merchant = _dataset()["merchants"].get(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return _copy(merchant)


@app.get("/api/merchants/{merchant_id}/business-hours")
def get_business_hours(merchant_id: str):
    dataset = _dataset()
    merchant = dataset["merchants"].get(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    hours = dataset["businessHours"].get(merchant["businessHoursId"])
    if not hours:
        raise HTTPException(status_code=404, detail="Business hours not found")
    return _copy(hours)


@app.get("/api/pois")
def list_pois(scenario: Optional[str] = Query(None)):
    return _copy(_pois_for_scenario(_dataset(), scenario))


@app.get("/api/pois/nearby")
def list_nearby_pois(scenario: Optional[str] = Query(None)):
    return _copy([poi for poi in _pois_for_scenario(_dataset(), scenario) if poi["status"] == "normal"])


@app.get("/api/pois/{poi_id}")
def get_poi(poi_id: str, scenario: Optional[str] = Query(None)):
    for poi in _pois_for_scenario(_dataset(), scenario):
        if poi["poiId"] == poi_id:
            return _copy(poi)
    raise HTTPException(status_code=404, detail="POI not found")


@app.get("/api/hotspots")
def list_hotspots(scenario: Optional[str] = Query(None)):
    return _copy([poi for poi in _pois_for_scenario(_dataset(), scenario) if poi["source"] == "hotspot"])


@app.get("/api/weather")
def get_weather(date_key: str = Query("nearest_weekend", alias="dateKey")):
    for item in _dataset()["weather"]:
        if item["date"] == date_key:
            return _copy(item)
    raise HTTPException(status_code=404, detail="Weather not found")

