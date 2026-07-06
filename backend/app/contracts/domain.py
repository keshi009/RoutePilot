"""领域模型：用户、订单、商家、兴趣信号、营业时间、POI、天气。

从旧 models.py 迁移到 Pydantic v2，保留原有业务字段（含 reservation_risk /
queue_risk / usable_time_windows / status 等关键事实）。对外用 camelCase alias。
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import Location, TimeWindow


class UserProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(default="", alias="userId")
    display_name: str = Field(default="", alias="displayName")
    city: str = ""
    current_location: Location = Field(default_factory=Location, alias="currentLocation")
    weekend_preferred_window: TimeWindow = Field(default_factory=TimeWindow, alias="weekendPreferredWindow")
    preference_tags: List[str] = Field(default_factory=list, alias="preferenceTags")


class InterestSignal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    signal_id: str = Field(default="", alias="signalId")
    source: Literal["favorite", "browse", "search", "like", "share", "purchase", "checkin"] = "browse"
    label: str = ""
    weight: float = 0.0
    related_categories: List[str] = Field(default_factory=list, alias="relatedCategories")


class BusinessDay(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    weekday: int = Field(default=0, ge=0, le=6)
    open_time: str = Field(default="", alias="openTime")
    close_time: str = Field(default="", alias="closeTime")
    is_closed: bool = Field(default=False, alias="isClosed")


class BusinessHours(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    merchant_id: str = Field(default="", alias="merchantId")
    weekly: List[BusinessDay] = Field(default_factory=list)
    special_closed_dates: List[str] = Field(default_factory=list, alias="specialClosedDates")
    notes: List[str] = Field(default_factory=list)


class Merchant(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    merchant_id: str = Field(default="", alias="merchantId")
    name: str = ""
    category: str = ""
    address: str = ""
    location: Location = Field(default_factory=Location)
    rating: float = 0.0
    avg_price: int = Field(default=0, alias="avgPrice")
    status: Literal["normal", "closed", "abnormal"] = "normal"
    reservation_required: bool = Field(default=False, alias="reservationRequired")
    reservation_risk: int = Field(default=0, alias="reservationRisk", ge=0, le=100)
    queue_risk: int = Field(default=0, alias="queueRisk", ge=0, le=100)
    image_url: str = Field(default="", alias="imageUrl")
    business_hours_id: str = Field(default="", alias="businessHoursId")


class Order(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(default="", alias="orderId")
    user_id: str = Field(default="", alias="userId")
    merchant_id: str = Field(default="", alias="merchantId")
    title: str = ""
    category: str = ""
    status: Literal["unused", "used", "refunded", "expired"] = "unused"
    valid_from: str = Field(default="", alias="validFrom")
    valid_until: str = Field(default="", alias="validUntil")
    usable_weekdays: List[int] = Field(default_factory=list, alias="usableWeekdays")
    usable_time_windows: List[TimeWindow] = Field(default_factory=list, alias="usableTimeWindows")
    price: int = 0
    value: int = 0
    needs_reservation: bool = Field(default=False, alias="needsReservation")
    tags: List[str] = Field(default_factory=list)
    image_url: str = Field(default="", alias="imageUrl")


class Poi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    poi_id: str = Field(default="", alias="poiId")
    name: str = ""
    category: str = ""
    source: Literal["interest", "hotspot", "nearby", "merchant"] = "nearby"
    location: Location = Field(default_factory=Location)
    rating: float = 0.0
    heat: int = Field(default=0, ge=0, le=100)
    avg_price: int = Field(default=0, alias="avgPrice")
    status: Literal["normal", "closed", "abnormal"] = "normal"
    recommended_tags: List[str] = Field(default_factory=list, alias="recommendedTags")
    action_type: Literal["view", "browse", "purchase_placeholder"] = Field(default="view", alias="actionType")
    open_time: str = Field(default="", alias="openTime")
    close_time: str = Field(default="", alias="closeTime")
    image_url: str = Field(default="", alias="imageUrl")


class WeatherSnapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: str = ""
    condition: str = ""
    temperature: str = ""
    outdoor_score: int = Field(default=0, alias="outdoorScore", ge=0, le=100)
    tips: List[str] = Field(default_factory=list)
