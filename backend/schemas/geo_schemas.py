
from pydantic import BaseModel, Field
from typing import List, Literal, Dict
class LocationRequest(BaseModel):
    address: str
    latitude: float
    longitude: float
class GeoSignal(BaseModel):
    poi_name: str
    poi_type: Literal["university", "office"]
    headcount: int
    distance_m: int
    travel_time_min: int
    reach_score: float
    latitude: float = Field(..., description="POI latitude")
    longitude: float = Field(..., description="POI longitude")
class MarketNeedReport(BaseModel):
    demand_hotspots: List[GeoSignal]; competitor_count: int; median_price: int; price_gap_pct: float; pain_topics: Dict[str, float]; final_score: float; verdict: Literal["PASS", "FAIL"]
