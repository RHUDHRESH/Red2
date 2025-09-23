
import asyncio
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from schemas.geo_schemas import MarketNeedReport, GeoSignal
from services.google_maps_service import POI
from services.registry import get_services

class MarketAnalysisState(TypedDict):
    initial_request: dict
    geocoded_location: dict
    nearby_pois: List[POI]
    pois_with_travel_times: List[POI]
    final_report: MarketNeedReport
    error: str | None

async def geocode_location(state: MarketAnalysisState) -> MarketAnalysisState:
    print("--- Starting: Geocode Location ---")
    try:
        location = state['initial_request']
        lat, lng = location['latitude'], location['longitude']
        geocoded = await get_services().maps.geocode(lat, lng)
        if not geocoded: raise ValueError("Geocoding failed.")
        state['geocoded_location'] = geocoded
        print(f"  > Success: Geocoded to {geocoded.get('formatted_address')}")
        return state
    except Exception as e:
        state['error'] = f"Failed to geocode: {e}"
        return state

async def scan_for_pois(state: MarketAnalysisState) -> MarketAnalysisState:
    print("--- Starting: Scan for POIs ---")
    if state.get('error'): return state
    try:
        location = (state['geocoded_location']['geometry']['location']['lat'], state['geocoded_location']['geometry']['location']['lng'])
        svc = get_services().maps
        tasks = [
            svc.nearby_search(location, radius=2000, poi_type='university', keyword='university'),
            svc.nearby_search(location, radius=2000, keyword='corporate office')
        ]
        results = await asyncio.gather(*tasks)
        all_pois = [poi for sublist in results for poi in sublist]
        state['nearby_pois'] = all_pois
        print(f"  > Success: Found {len(all_pois)} POIs.")
        return state
    except Exception as e:
        state['error'] = f"Failed to scan for POIs: {e}"
        return state

async def calculate_travel_times(state: MarketAnalysisState) -> MarketAnalysisState:
    print("--- Starting: Calculate Travel Times ---")
    if state.get('error') or not state.get('nearby_pois'): return state
    try:
        origin = (state['geocoded_location']['geometry']['location']['lat'], state['geocoded_location']['geometry']['location']['lng'])
        pois_with_times = await get_services().maps.get_travel_times(origin, state['nearby_pois'])
        state['pois_with_travel_times'] = pois_with_times
        print(f"  > Success: Calculated travel times for {len(pois_with_times)} POIs.")
        return state
    except Exception as e:
        state['error'] = f"Failed travel time calculation: {e}"
        return state

def calculate_scores_and_verdict(state: MarketAnalysisState) -> MarketAnalysisState:
    print("--- Starting: Score Calculation ---")
    if state.get('error') or not state.get('pois_with_travel_times'): return state
    hot_poi_signals = []
    total_reach_score = 0
    for poi in state['pois_with_travel_times']:
        if poi.travel_time_min > 0:
            headcount = 5000 if 'university' in poi.types else 1500
            reach_score = headcount / poi.travel_time_min
            if reach_score >= 200:
                signal = GeoSignal(
                    poi_name=poi.name,
                    poi_type="university" if 'university' in poi.types else "office",
                    headcount=headcount,
                    distance_m=poi.distance_m,
                    travel_time_min=poi.travel_time_min,
                    reach_score=reach_score,
                    latitude=poi.location[0],
                    longitude=poi.location[1],
                )
                hot_poi_signals.append(signal)
                total_reach_score += reach_score

    price_gap_pct, pain_density = 15.0, 25.0 # Placeholders
    avg_reach_hot = (total_reach_score / len(hot_poi_signals)) if hot_poi_signals else 0
    final_score = (0.5 * avg_reach_hot) + (0.3 * price_gap_pct) + (0.2 * pain_density)
    verdict = "PASS" if final_score >= 120 and len(hot_poi_signals) > 0 else "FAIL"

    state['final_report'] = MarketNeedReport(demand_hotspots=hot_poi_signals, competitor_count=10, median_price=250, price_gap_pct=price_gap_pct, pain_topics={"speed": 0.3, "price": 0.5}, final_score=final_score, verdict=verdict)
    print(f"  > Success: Final score {final_score:.2f}. Verdict: {verdict}")
    return state

workflow = StateGraph(MarketAnalysisState)
workflow.add_node("geocode", geocode_location)
workflow.add_node("scan_pois", scan_for_pois)
workflow.add_node("get_travel_times", calculate_travel_times)
workflow.add_node("calculate_scores", calculate_scores_and_verdict)
workflow.set_entry_point("geocode")
workflow.add_edge("geocode", "scan_pois")
workflow.add_edge("scan_pois", "get_travel_times")
workflow.add_edge("get_travel_times", "calculate_scores")
workflow.add_edge("calculate_scores", END)
market_analysis_agent = workflow.compile()

async def run_market_analysis_agent(location_request: dict):
    final_state = await market_analysis_agent.ainvoke({"initial_request": location_request})
    if final_state.get('error'): return {"error": final_state['error']}
    return final_state['final_report'].model_dump()
