
import googlemaps
import asyncio
from functools import partial
from typing import List, Tuple
from pydantic import BaseModel
from core.config import settings
class POI(BaseModel):
    name: str; location: Tuple[float, float]; types: List[str]; user_ratings_total: int = 0; distance_m: int = 0; travel_time_min: int = 0
class GoogleMapsService:
    def __init__(self):
        key = settings.GOOGLE_MAPS_API_KEY
        try:
            if not key or "your_actual" in str(key):
                self.client = None
            else:
                self.client = googlemaps.Client(key=key)
        except Exception:
            self.client = None
    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        call = partial(func, *args, **kwargs) if kwargs else partial(func, *args)
        return await loop.run_in_executor(None, call)
    async def geocode(self, lat: float, lng: float):
        if not self.client:
            return None
        result = await self._run_in_executor(self.client.reverse_geocode, (lat, lng))
        return result[0] if result else None
    async def nearby_search(self, location: tuple, radius: int, poi_type: str = None, keyword: str = None):
        params = {'location': location, 'radius': radius}
        if poi_type:
            params['type'] = poi_type
        if keyword:
            params['keyword'] = keyword
        if not self.client:
            return []
        response = await self._run_in_executor(self.client.places_nearby, **params)
        return [POI(name=p.get('name','N/A'), location=(p['geometry']['location']['lat'], p['geometry']['location']['lng']), types=p.get('types',[]), user_ratings_total=p.get('user_ratings_total',0)) for p in response.get('results', [])]
    async def get_travel_times(self, origin: tuple, destinations: List[POI]):
        if not destinations: return []
        dest_coords = [d.location for d in destinations]
        if not self.client:
            return destinations
        response = await self._run_in_executor(self.client.distance_matrix, origin, dest_coords, mode="driving")
        updated_pois = []
        for i, poi in enumerate(destinations):
            element = response['rows'][0]['elements'][i]
            if element['status'] == 'OK':
                poi.distance_m = element['distance']['value']
                poi.travel_time_min = round(element['duration']['value'] / 60)
                updated_pois.append(poi)
        return updated_pois
