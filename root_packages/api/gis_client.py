import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .openai_client import UserPreferences


@dataclass
class Place:
    id: str
    name: str
    address: str
    rating: Optional[float]
    reviews_count: Optional[int]
    categories: List[str]
    coordinates: Dict[str, float]
    working_hours: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    photo_url: Optional[str]


class GISClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://catalog.api.2gis.com/3.0/items"
        
    async def search_places(
        self, 
        user_preferences: UserPreferences,
        location: Optional[Dict[str, float]] = None,
        radius: int = 5000,
        limit: int = 10
    ) -> List[Place]:
        params = self._build_search_params(user_preferences, location, radius, limit)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        logging.error(f"2GIS API error: {response.status}")
                        return []
                    
                    data = await response.json()
                    return self._parse_places(data)
                    
            except Exception as e:
                logging.error(f"Error searching places: {e}")
                return []

    def _build_search_params(
        self, 
        preferences: UserPreferences, 
        location: Optional[Dict[str, float]], 
        radius: int, 
        limit: int
    ) -> Dict[str, Any]:
        params = {
            "fields": "items.point,items.adm_div,items.contact_groups,items.rubrics,items.reviews,items.schedule",
            "page_size": limit
        }
        
        if self.api_key:
            params["key"] = self.api_key
            
        # Добавляем геопозицию если есть
        if location:
            params["point"] = f"{location['lon']},{location['lat']}"
            params["radius"] = radius
        
        # Формируем поисковый запрос на основе предпочтений
        query_parts = []
        
        if preferences.category:
            category_mapping = {
                "ресторан": "restaurant",
                "кафе": "cafe",
                "развлечения": "entertainment",
                "спорт": "sport",
                "культура": "culture",
                "шоппинг": "shopping",
                "красота": "beauty",
                "услуги": "service"
            }
            if preferences.category in category_mapping:
                query_parts.append(category_mapping[preferences.category])
                
        if preferences.activity_type and preferences.activity_type != preferences.category:
            query_parts.append(preferences.activity_type)
            
        if preferences.specific_requirements:
            query_parts.extend(preferences.specific_requirements)
        
        if query_parts:
            params["q"] = " ".join(query_parts)
        else:
            # Если нет конкретных предпочтений, ищем популярные места
            params["q"] = "популярные места"
            
        return params

    def _parse_places(self, api_response: Dict) -> List[Place]:
        places = []
        items = api_response.get("result", {}).get("items", [])
        
        for item in items:
            try:
                place = Place(
                    id=item.get("id", ""),
                    name=item.get("name", "Без названия"),
                    address=self._extract_address(item),
                    rating=self._extract_rating(item),
                    reviews_count=self._extract_reviews_count(item),
                    categories=self._extract_categories(item),
                    coordinates=self._extract_coordinates(item),
                    working_hours=self._extract_working_hours(item),
                    phone=self._extract_phone(item),
                    website=self._extract_website(item),
                    photo_url=self._extract_photo(item)
                )
                places.append(place)
            except Exception as e:
                logging.warning(f"Error parsing place item: {e}")
                continue
                
        return places

    def _extract_address(self, item: Dict) -> str:
        adm_div = item.get("adm_div", [])
        if adm_div:
            return adm_div[-1].get("name", "Адрес не указан")
        return item.get("address_name", "Адрес не указан")

    def _extract_rating(self, item: Dict) -> Optional[float]:
        reviews = item.get("reviews")
        if reviews:
            return reviews.get("rating")
        return None

    def _extract_reviews_count(self, item: Dict) -> Optional[int]:
        reviews = item.get("reviews")
        if reviews:
            return reviews.get("count")
        return None

    def _extract_categories(self, item: Dict) -> List[str]:
        rubrics = item.get("rubrics", [])
        return [rubric.get("name", "") for rubric in rubrics if rubric.get("name")]

    def _extract_coordinates(self, item: Dict) -> Dict[str, float]:
        point = item.get("point", {})
        return {
            "lat": point.get("lat", 0.0),
            "lon": point.get("lon", 0.0)
        }

    def _extract_working_hours(self, item: Dict) -> Optional[str]:
        schedule = item.get("schedule")
        if schedule:
            return schedule.get("Пн", "Не указано")
        return None

    def _extract_phone(self, item: Dict) -> Optional[str]:
        contact_groups = item.get("contact_groups", [])
        for group in contact_groups:
            contacts = group.get("contacts", [])
            for contact in contacts:
                if contact.get("type") == "phone":
                    return contact.get("value")
        return None

    def _extract_website(self, item: Dict) -> Optional[str]:
        contact_groups = item.get("contact_groups", [])
        for group in contact_groups:
            contacts = group.get("contacts", [])
            for contact in contacts:
                if contact.get("type") == "website":
                    return contact.get("value")
        return None

    def _extract_photo(self, item: Dict) -> Optional[str]:
        # В базовой версии API фото может быть недоступно
        return None

    def format_place_for_user(self, place: Place) -> str:
        text = f"📍 <b>{place.name}</b>\n"
        text += f"📮 {place.address}\n"
        
        if place.rating:
            stars = "⭐" * int(place.rating)
            text += f"{stars} {place.rating}"
            if place.reviews_count:
                text += f" ({place.reviews_count} отзывов)"
            text += "\n"
            
        if place.categories:
            text += f"🏷 {', '.join(place.categories[:2])}\n"
            
        if place.working_hours:
            text += f"🕒 {place.working_hours}\n"
            
        if place.phone:
            text += f"📞 {place.phone}\n"
            
        if place.website:
            text += f"🌐 {place.website}\n"
            
        return text 