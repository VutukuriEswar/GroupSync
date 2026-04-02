import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set
import random
import math
import asyncio
import json
import httpx
import threading
import os
import logging
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

FEATURE_DIM = 22
ACTIONS = ["dining", "movie", "outdoor_relaxed", "outdoor_active", "cultural", "entertainment"]
TRAVEL_SPEED_KMH = 35.0

MAX_BUDGET_MAP = {"free": 0, "low": 500, "medium": 1500, "high": 5000}

PREF_ALLOWED = {
    "indoor": {"dining", "movie", "cultural", "entertainment"},
    "outdoor": {"outdoor_relaxed", "outdoor_active", "dining"},
    "both": set(ACTIONS),
}

GENRES = ["action", "comedy", "drama", "horror", "romance", "thriller", "sci-fi", 
          "animation", "documentary", "family", "adventure", "mystery", "fantasy"]
CUISINES = ["indian", "chinese", "italian", "mexican", "thai", "japanese", 
            "american", "mediterranean", "korean", "vietnamese", "continental",
            "mughlai", "north_indian", "seafood", "vegetarian", "vegan"]
ACTIVITY_VIBES = ["relaxing", "adventurous", "romantic", "family_friendly", 
                  "budget_friendly", "luxurious", "social", "cultural", "active"]
TIME_SLOTS = ["morning", "afternoon", "evening", "night", "late_night"]

@dataclass
class ActivityAttributes:
    genres: List[str] = field(default_factory=list)
    cuisines: List[str] = field(default_factory=list)
    vibes: List[str] = field(default_factory=list)
    time_slots: List[str] = field(default_factory=list)
    suitable_for_groups: bool = True
    indoor_outdoor: str = "both"
    age_restriction: str = "all"
    booking_required: bool = False
    popularity_score: float = 0.5
    rating: float = 3.5
    
    def to_feature_vector(self, pref_genres: List[str], pref_cuisines: List[str], 
                          pref_vibes: List[str], time_slot: str) -> np.ndarray:
        genre_match = len(set(self.genres) & set(pref_genres)) / max(len(pref_genres), 1) if pref_genres else 0.5
        cuisine_match = len(set(self.cuisines) & set(pref_cuisines)) / max(len(pref_cuisines), 1) if pref_cuisines else 0.5
        vibe_match = len(set(self.vibes) & set(pref_vibes)) / max(len(pref_vibes), 1) if pref_vibes else 0.5
        time_match = 1.0 if time_slot in self.time_slots or not self.time_slots else 0.3
        
        return np.array([
            genre_match,
            cuisine_match,
            vibe_match,
            time_match,
            1.0 if self.suitable_for_groups else 0.0,
            self.popularity_score,
            self.rating / 5.0,
            1.0 if self.indoor_outdoor in ("indoor", "both") else 0.0,
            1.0 if self.indoor_outdoor in ("outdoor", "both") else 0.0,
            1.0 if self.age_restriction == "all" else 0.0,
            1.0 if self.booking_required else 0.0,
            len(self.genres) / 5.0,
            len(self.cuisines) / 5.0,
            len(self.vibes) / 5.0,
            len(self.time_slots) / 5.0,
            1.0 if "morning" in self.time_slots else 0.0,
            1.0 if "afternoon" in self.time_slots else 0.0,
            1.0 if "evening" in self.time_slots else 0.0,
            1.0 if "night" in self.time_slots else 0.0,
            1.0,
        ], dtype=np.float64)

@dataclass
class ActivityItem:
    name: str
    category: str
    cost: int
    duration: int
    lat: float = 0.0
    lon: float = 0.0
    attributes: ActivityAttributes = field(default_factory=ActivityAttributes)
    source: str = "sample"
    url: str = ""
    address: str = ""
    showtimes: List[str] = field(default_factory=list)
    phone: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.category,
            "category": self.category,
            "cost": self.cost,
            "duration": self.duration,
            "lat": self.lat,
            "lon": self.lon,
            "genres": self.attributes.genres,
            "cuisines": self.attributes.cuisines,
            "vibes": self.attributes.vibes,
            "time_slots": self.attributes.time_slots,
            "suitable_for_groups": self.attributes.suitable_for_groups,
            "indoor_outdoor": self.attributes.indoor_outdoor,
            "rating": self.attributes.rating,
            "popularity_score": self.attributes.popularity_score,
            "source": self.source,
            "url": self.url,
            "address": self.address,
            "showtimes": self.showtimes,
            "phone": self.phone,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ActivityItem":
        attrs = ActivityAttributes(
            genres=data.get("genres", []),
            cuisines=data.get("cuisines", []),
            vibes=data.get("vibes", []),
            time_slots=data.get("time_slots", []),
            suitable_for_groups=data.get("suitable_for_groups", True),
            indoor_outdoor=data.get("indoor_outdoor", "both"),
            rating=data.get("rating", 3.5),
            popularity_score=data.get("popularity_score", 0.5),
        )
        return cls(
            name=data.get("name", ""),
            category=data.get("category", data.get("type", "dining")),
            cost=data.get("cost", 0),
            duration=data.get("duration", 60),
            lat=data.get("lat", 0.0),
            lon=data.get("lon", 0.0),
            attributes=attrs,
            source=data.get("source", "sample"),
            url=data.get("url", ""),
            address=data.get("address", ""),
            showtimes=data.get("showtimes", []),
            phone=data.get("phone", ""),
            description=data.get("description", ""),
        )

class WebDataFetcher:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(3)
        self._cache: Dict[str, Tuple[List[Dict], float]] = {}
        self._cache_duration = 3600
        self._cli_available = None
    
    async def _overpass_query(self, query: str) -> List[Dict]:
        mirrors = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter",
            "https://overpass.osm.ch/api/interpreter",
            "https://overpass.osm.rambler.ru/cgi/interpreter",
        ]
        max_retries = 3
        for i in range(max_retries):
            url = random.choice(mirrors)
            delay = (2 ** i) + random.random()
            if i > 0:
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(url, data={"data": query})
                    if resp.status_code == 200:
                        return resp.json().get("elements", [])
                    elif resp.status_code == 429:
                        logger.warning(f"Mirror {url} hit 429 rate limit. Retrying...")
                    else:
                        logger.warning(f"Mirror {url} returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Accessing mirror {url} failed: {e}")
        return []
    
    def _get_cache_key(self, query: str, location: str) -> str:
        return f"{query}_{location}".lower().replace(" ", "_")
    
    async def search_movies(self, lat: float, lon: float, genres: List[str] = None) -> List[ActivityItem]:
        cache_key = f"movies_real_{lat}_{lon}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if datetime.now().timestamp() - ts < self._cache_duration:
                return [ActivityItem.from_dict(d) for d in data]
        query = f"""[out:json][timeout:25];
        (node["amenity"="cinema"](around:10000,{lat},{lon});
         way["amenity"="cinema"](around:10000,{lat},{lon}););
        out center;"""
        elements = await self._overpass_query(query)
        if not elements: return self._get_sample_movies("Current", genres)
        movies_pool = []
        try:
            search_query = "current movies playing in Vijayawada cinemas today"
            results = await self._search_web_internal(search_query)
            movies_pool = self._extract_movie_list_from_search(results)
        except Exception as e:
            logger.warning(f"Movie scraping failed: {e}")
            movies_pool = ["Global Blockbuster", "Action Epic", "Comedy Special"]
        items = []
        for el in elements:
            base_name = el.get("tags", {}).get("name", "Cinema")
            movie_title = random.choice(movies_pool) if movies_pool else "Now Playing"
            display_name = f"{base_name}: {movie_title}"
            items.append(ActivityItem(
                name=display_name,
                category="movie",
                cost=random.randint(250, 450),
                duration=150,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    genres=genres or ["drama", "action"],
                    vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening", "night"],
                    indoor_outdoor="indoor",
                    popularity_score=0.8,
                    rating=4.2
                ),
                source="overpass_scraped"
            ))
        self._cache[cache_key] = ([i.to_dict() for i in items], datetime.now().timestamp())
        return items

    async def _search_web_internal(self, query: str) -> List[Dict]:
        return [{"name": "Dhurandhar", "snippet": "Action"}, {"name": "Project Hail Mary", "snippet": "Sci-Fi"}]

    def _extract_movie_list_from_search(self, results: List) -> List[str]:
        return ["Dhurandhar The Revenge", "Project Hail Mary", "Ustaad Bhagat Singh", "The Super Mario Galaxy Movie", "Ready Or Not 2"]
    
    async def search_restaurants(self, lat: float, lon: float, cuisines: List[str] = None,
                                 budget: str = "medium") -> List[ActivityItem]:
        cache_key = f"rest_{lat}_{lon}_{budget}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if datetime.now().timestamp() - ts < self._cache_duration:
                return [ActivityItem.from_dict(d) for d in data]
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"~"restaurant|cafe|fast_food|pizzeria"](around:5000,{lat},{lon});
          way["amenity"~"restaurant|cafe|fast_food|pizzeria"](around:5000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "Local Eatery")
            cuisine_tag = tags.get("cuisine", "").lower().split(";")
            found_cuisines = [c.strip() for c in cuisine_tag if c.strip() in CUISINES] or ["indian"]
            cost = self._get_realistic_cost("dining", tags.get("cuisine", ""), budget)
            items.append(ActivityItem(
                name=name,
                category="dining",
                cost=cost,
                duration=60,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    cuisines=found_cuisines,
                    vibes=["social", "casual"],
                    time_slots=["morning", "afternoon", "evening", "night"],
                    indoor_outdoor="indoor",
                    rating=random.uniform(4.0, 4.8)
                ),
                source="overpass"
            ))
        if not items:
            items = self._get_sample_restaurants("Current", cuisines, budget)
        self._cache[cache_key] = ([i.to_dict() for i in items], datetime.now().timestamp())
        return items
    
    async def search_events(self, lat: float, lon: float, event_type: str = "all") -> List[ActivityItem]:
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"~"attraction|museum|gallery|zoo|theme_park"](around:15000,{lat},{lon});
          way["tourism"~"attraction|museum|gallery|zoo|theme_park"](around:15000,{lat},{lon});
          node["leisure"~"amusement_arcade|bowling_alley|karting|sports_centre"](around:15000,{lat},{lon});
          way["leisure"~"amusement_arcade|bowling_alley|karting|sports_centre"](around:15000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        blacklist = ["aadhar", "seva", "kendram", "office", "bank", "department", 
                     "municipality", "development", "service", "center", "corporation"]
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "Local Attraction")
            if any(term in name.lower() for term in blacklist):
                continue
            items.append(ActivityItem(
                name=name,
                category="cultural" if "museum" in tags.values() else "entertainment",
                cost=random.randint(100, 500),
                duration=120,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    vibes=["cultural", "social"],
                    time_slots=["morning", "afternoon", "evening"],
                    indoor_outdoor="indoor",
                    rating=4.2
                ),
                source="overpass"
            ))
        if not items:
            items = self._get_sample_events("Current", event_type)
        return items
    
    async def search_outdoor_activities(self, lat: float, lon: float, activity_type: str,
                                        vibe: str = None) -> List[ActivityItem]:
        query = f"""
        [out:json][timeout:25];
        (
          node["leisure"~"park|garden|nature_reserve|playground"](around:8000,{lat},{lon});
          way["leisure"~"park|garden|nature_reserve|playground"](around:8000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        blacklist = ["aadhar", "seva", "kendram", "office", "bank", "department", 
                     "municipality", "development", "service", "center", "corporation"]
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "Local Park")
            if any(term in name.lower() for term in blacklist):
                continue
            items.append(ActivityItem(
                name=name,
                category="outdoor_relaxed",
                cost=0,
                duration=90,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    vibes=["relaxing", "family_friendly"],
                    time_slots=["morning", "afternoon", "evening"],
                    indoor_outdoor="outdoor",
                    rating=4.5
                ),
                source="overpass"
            ))
        if items:
            pass
        if not items:
            items = self._get_sample_outdoor("Current", activity_type)
        return items

    def _get_realistic_cost(self, category: str, sub_type: str, budget_tier: str) -> int:
        profiles = {
            "dining": {"breakfast": (80, 250), "lunch": (200, 600), "dinner": (350, 1200)},
            "movie": {"default": (250, 500)},
            "cultural": {"default": (300, 1500)},
            "entertainment": {"default": (200, 1000)},
            "outdoor_relaxed": {"default": (0, 100)},
            "outdoor_active": {"default": (50, 400)}
        }
        profile = profiles.get(category, {"default": (100, 500)})
        low, high = profile.get("default", profile.get(list(profile.keys())[0]))
        if budget_tier == "low":
            return random.randint(low, (low + high) // 2)
        elif budget_tier == "high":
            return random.randint((low + high) // 2, high * 2)
        else:
            return random.randint(low, high)
    
    async def _parse_movie_search_results(self, results: List, location: str, 
                                           preferred_genres: List[str]) -> List[ActivityItem]:
        items = []
        seen = set()
        for result in results:
            name = result.get("name", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            movie_name = self._extract_movie_name(name, snippet)
            if not movie_name or movie_name in seen:
                continue
            seen.add(movie_name)
            genres = self._extract_genres(f"{name} {snippet}")
            if preferred_genres and genres:
                if not any(g in genres for g in preferred_genres):
                    continue
            showtimes = self._extract_showtimes(snippet)
            cost = 14
            if "imax" in name.lower() or "imax" in snippet.lower():
                cost = 22
            elif "premium" in snippet.lower() or "gold" in snippet.lower():
                cost = 18
            elif "morning" in snippet.lower():
                cost = 10
            item = ActivityItem(
                name=movie_name,
                category="movie",
                cost=cost,
                duration=random.randint(120, 180),
                attributes=ActivityAttributes(
                    genres=genres,
                    vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening", "night"],
                    suitable_for_groups=True,
                    indoor_outdoor="indoor",
                    booking_required=True,
                    popularity_score=random.uniform(0.6, 1.0),
                    rating=random.uniform(3.0, 4.5),
                ),
                source="web_search",
                url=url,
                showtimes=showtimes,
            )
            items.append(item)
        return items[:15]
    
    async def _parse_restaurant_search_results(self, results: List, location: str,
                                                cuisines: List[str], budget: str) -> List[ActivityItem]:
        items = []
        seen = set()
        max_cost = MAX_BUDGET_MAP.get(budget, 60)
        for result in results:
            name = result.get("name", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            rest_name = self._extract_restaurant_name(name, snippet)
            if not rest_name or rest_name in seen:
                continue
            seen.add(rest_name)
            found_cuisines = self._extract_cuisines(f"{name} {snippet}")
            if cuisines and found_cuisines:
                if not any(c in found_cuisines for c in cuisines):
                    continue
            cost = self._estimate_restaurant_cost(snippet, budget)
            if cost > max_cost and budget != "high":
                continue
            item = ActivityItem(
                name=rest_name,
                category="dining",
                cost=cost,
                duration=random.randint(45, 90),
                attributes=ActivityAttributes(
                    cuisines=found_cuisines,
                    vibes=self._extract_vibes(snippet),
                    time_slots=["morning", "afternoon", "evening", "night"],
                    suitable_for_groups=True,
                    indoor_outdoor="indoor",
                    popularity_score=random.uniform(0.5, 1.0),
                    rating=random.uniform(3.5, 4.8),
                ),
                source="web_search",
                url=url,
                description=snippet[:200],
            )
            items.append(item)
        return items[:15]
    
    async def _parse_event_search_results(self, results: List, location: str,
                                           event_type: str) -> List[ActivityItem]:
        items = []
        seen = set()
        for result in results:
            name = result.get("name", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            event_name = self._extract_event_name(name, snippet)
            if not event_name or event_name in seen:
                continue
            seen.add(event_name)
            category = self._determine_event_category(snippet)
            cost = self._extract_event_cost(snippet)
            time_slots = self._extract_time_slots(snippet)
            item = ActivityItem(
                name=event_name,
                category=category,
                cost=cost,
                duration=random.randint(60, 180),
                attributes=ActivityAttributes(
                    genres=self._extract_genres(snippet),
                    vibes=self._extract_vibes(snippet),
                    time_slots=time_slots,
                    suitable_for_groups=True,
                    indoor_outdoor="indoor" if "indoor" in snippet.lower() else "outdoor",
                    booking_required=True,
                    popularity_score=random.uniform(0.6, 1.0),
                    rating=random.uniform(3.5, 4.5),
                ),
                source="web_search",
                url=url,
                description=snippet[:200],
            )
            items.append(item)
        return items[:15]
    
    async def _parse_outdoor_search_results(self, results: List, location: str,
                                             activity_type: str) -> List[ActivityItem]:
        items = []
        seen = set()
        for result in results:
            name = result.get("name", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            activity_name = self._extract_location_name(name, snippet)
            if not activity_name or activity_name in seen:
                continue
            seen.add(activity_name)
            category = "outdoor_relaxed" if "relaxed" in activity_type else "outdoor_active"
            if "park" in snippet.lower() or "garden" in snippet.lower():
                category = "outdoor_relaxed"
            elif "sports" in snippet.lower() or "adventure" in snippet.lower():
                category = "outdoor_active"
            cost = self._extract_outdoor_cost(snippet)
            item = ActivityItem(
                name=activity_name,
                category=category,
                cost=cost,
                duration=random.randint(60, 180),
                attributes=ActivityAttributes(
                    vibes=self._extract_vibes(snippet),
                    time_slots=["morning", "afternoon", "evening"],
                    suitable_for_groups=True,
                    indoor_outdoor="outdoor",
                    popularity_score=random.uniform(0.5, 0.9),
                    rating=random.uniform(3.5, 4.5),
                ),
                source="web_search",
                url=url,
                description=snippet[:200],
            )
            items.append(item)
        return items[:10]

    def _extract_movie_name(self, title: str, snippet: str) -> str:
        title = re.sub(r'\s*[-|]\s*(BookMyShow|IMDb|Rotten Tomatoes|Showtimes|Movie).*$', '', title, flags=re.I)
        title = re.sub(r'\s*\(\d{4}\)', '', title)
        title = re.sub(r'\s*:\s*Showtimes.*$', '', title, flags=re.I)
        if "showtimes" in title.lower() or "movie" in title.lower():
            patterns = [
                r'([A-Z][A-Za-z\s]+(?:\d)?(?:\s*:\s*\w+)?)',
                r'(?:watch|stream|book)\s+([A-Z][A-Za-z\s]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, snippet)
                if match:
                    return match.group(1).strip()
        return title.strip() if len(title) > 2 and len(title) < 80 else ""
    
    def _extract_genres(self, text: str) -> List[str]:
        text_lower = text.lower()
        found = []
        for genre in GENRES:
            if genre in text_lower or genre.replace("-", "") in text_lower:
                found.append(genre)
        return found[:3] if found else ["drama"]
    
    def _extract_cuisines(self, text: str) -> List[str]:
        text_lower = text.lower()
        found = []
        for cuisine in CUISINES:
            if cuisine.replace("_", " ") in text_lower or cuisine in text_lower:
                found.append(cuisine)
        return found[:3] if found else ["indian"]
    
    def _extract_vibes(self, text: str) -> List[str]:
        text_lower = text.lower()
        found = []
        vibe_keywords = {
            "relaxing": ["relax", "peaceful", "calm", "serene", "quiet"],
            "adventurous": ["adventure", "thrill", "exciting", "extreme"],
            "romantic": ["romantic", "date", "intimate", "couples"],
            "family_friendly": ["family", "kids", "children", "all ages"],
            "budget_friendly": ["budget", "affordable", "cheap", "free"],
            "luxurious": ["luxury", "premium", "fine dining", "upscale"],
            "social": ["social", "group", "friends", "party"],
            "cultural": ["cultural", "heritage", "traditional", "historic"],
            "active": ["active", "fitness", "sports", "workout"],
        }
        for vibe, keywords in vibe_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found.append(vibe)
        return found[:3] if found else ["social"]
    
    def _extract_showtimes(self, text: str) -> List[str]:
        showtimes = []
        pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
        matches = re.findall(pattern, text)
        for match in matches[:5]:
            showtimes.append(match.upper())
        return showtimes
    
    def _extract_time_slots(self, text: str) -> List[str]:
        text_lower = text.lower()
        slots = []
        if any(w in text_lower for w in ["morning", "am", "breakfast"]):
            slots.append("morning")
        if any(w in text_lower for w in ["afternoon", "lunch", "noon"]):
            slots.append("afternoon")
        if any(w in text_lower for w in ["evening", "dinner", "pm"]):
            slots.append("evening")
        if any(w in text_lower for w in ["night", "late night", "midnight"]):
            slots.append("night")
        return slots if slots else ["afternoon", "evening"]
    
    def _extract_restaurant_name(self, title: str, snippet: str) -> str:
        title = re.sub(r'\s*[-|]\s*(Zomato|Swiggy|Dineout|Restaurant|Menu|Order).*$', '', title, flags=re.I)
        title = re.sub(r'\s*-\s*Reviews.*$', '', title, flags=re.I)
        return title.strip() if len(title) > 2 and len(title) < 80 else ""
    
    def _extract_event_name(self, title: str, snippet: str) -> str:
        title = re.sub(r'\s*[-|]\s*(BookMyShow|Insider|Eventbrite|Events).*$', '', title, flags=re.I)
        title = re.sub(r'\s*-\s*(Tickets|Book).*$', '', title, flags=re.I)
        return title.strip() if len(title) > 2 and len(title) < 100 else ""
    
    def _extract_location_name(self, title: str, snippet: str) -> str:
        title = re.sub(r'\s*[-|]\s*(Google Maps|TripAdvisor|Yelp).*$', '', title, flags=re.I)
        return title.strip() if len(title) > 2 and len(title) < 80 else ""
    
    def _estimate_restaurant_cost(self, snippet: str, budget: str) -> int:
        snippet_lower = snippet.lower()
        if "₹" in snippet or "rs." in snippet.lower():
            match = re.search(r'[₹rs.]\s*(\d+)', snippet, re.I)
            if match:
                return int(match.group(1))
        if any(w in snippet_lower for w in ["fine dining", "upscale", "luxury", "premium"]):
            return random.randint(40, 80)
        elif any(w in snippet_lower for w in ["casual", "mid-range", "casual dining"]):
            return random.randint(15, 35)
        elif any(w in snippet_lower for w in ["budget", "affordable", "cheap"]):
            return random.randint(5, 15)
        budget_costs = {"free": 0, "low": 12, "medium": 20, "high": 45}
        return budget_costs.get(budget, 20)
    
    def _determine_event_category(self, snippet: str) -> str:
        snippet_lower = snippet.lower()
        if any(w in snippet_lower for w in ["concert", "music", "live music", "band"]):
            return "entertainment"
        elif any(w in snippet_lower for w in ["museum", "gallery", "exhibition", "art"]):
            return "cultural"
        elif any(w in snippet_lower for w in ["comedy", "stand-up", "improv"]):
            return "entertainment"
        elif any(w in snippet_lower for w in ["theatre", "theater", "play", "drama"]):
            return "cultural"
        elif any(w in snippet_lower for w in ["food festival", "wine tasting", "food event"]):
            return "dining"
        return "entertainment"
    
    def _extract_event_cost(self, snippet: str) -> int:
        if "free" in snippet.lower():
            return 0
        match = re.search(r'[₹rs.$]\s*(\d+)', snippet, re.I)
        if match:
            return int(match.group(1))
        return random.randint(10, 40)
    
    def _extract_outdoor_cost(self, snippet: str) -> int:
        if "free" in snippet.lower():
            return 0
        match = re.search(r'[₹rs.$]\s*(\d+)', snippet, re.I)
        if match:
            return int(match.group(1))
        if any(w in snippet.lower() for w in ["adventure", "extreme", "tour"]):
            return random.randint(20, 60)
        elif any(w in snippet.lower() for w in ["park", "garden", "trail", "beach"]):
            return random.randint(0, 10)
        return random.randint(5, 25)

    def _get_sample_movies(self, location: str, genres: List[str] = None) -> List[ActivityItem]:
        sample_movies = [
            ActivityItem(name="Cineplex: Cosmic Adventure", category="movie", cost=14, duration=145,
                attributes=ActivityAttributes(genres=["sci-fi", "action", "adventure"], vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.85, rating=4.2)),
            ActivityItem(name="Cineplex: Love in Paris", category="movie", cost=14, duration=130,
                attributes=ActivityAttributes(genres=["romance", "drama"], vibes=["romantic", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.75, rating=4.0)),
            ActivityItem(name="Cineplex: Laugh Riot", category="movie", cost=14, duration=120,
                attributes=ActivityAttributes(genres=["comedy"], vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.80, rating=4.1)),
            ActivityItem(name="IMAX: Into the Deep", category="movie", cost=22, duration=150,
                attributes=ActivityAttributes(genres=["documentary", "adventure"], vibes=["educational", "social"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.70, rating=4.3)),
            ActivityItem(name="Cineplex: Thriller Night", category="movie", cost=14, duration=135,
                attributes=ActivityAttributes(genres=["thriller", "mystery"], vibes=["suspenseful", "social"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.72, rating=3.9)),
            ActivityItem(name="Cineplex: Family Fun", category="movie", cost=11, duration=100,
                attributes=ActivityAttributes(genres=["animation", "family", "comedy"], vibes=["family_friendly", "entertaining"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.88, rating=4.4)),
            ActivityItem(name="Cineplex: Action Blast", category="movie", cost=14, duration=140,
                attributes=ActivityAttributes(genres=["action", "adventure"], vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.82, rating=4.0)),
            ActivityItem(name="Arthouse: Indie Dreams", category="movie", cost=10, duration=125,
                attributes=ActivityAttributes(genres=["drama", "indie"], vibes=["cultural", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.55, rating=4.5)),
            ActivityItem(name="Cineplex: Horror Nights", category="movie", cost=14, duration=120,
                attributes=ActivityAttributes(genres=["horror", "thriller"], vibes=["suspenseful", "social"],
                    time_slots=["evening", "night", "late_night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.68, rating=3.7)),
            ActivityItem(name="Cineplex: The Epic Journey", category="movie", cost=16, duration=180,
                attributes=ActivityAttributes(genres=["action", "adventure", "fantasy"], vibes=["entertaining", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.90, rating=4.6)),
        ]
        if genres:
            sample_movies = [m for m in sample_movies 
                           if any(g in m.attributes.genres for g in genres)]
        for m in sample_movies:
            m.cost = 450 if m.cost < 15 else 800
            m.lat = 0.001 * random.uniform(-20, 20)
            m.lon = 0.001 * random.uniform(-20, 20)
        return sample_movies
    
    def _get_sample_restaurants(self, location: str, cuisines: List[str] = None,
                                 budget: str = "medium") -> List[ActivityItem]:
        max_cost = MAX_BUDGET_MAP.get(budget, 60)
        sample_restaurants = [
            ActivityItem(name="The Royal Indian Kitchen", category="dining", cost=18, duration=65,
                attributes=ActivityAttributes(cuisines=["indian", "north_indian"], vibes=["social", "luxurious"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.82, rating=4.3)),
            ActivityItem(name="Dragon Palace Chinese", category="dining", cost=16, duration=55,
                attributes=ActivityAttributes(cuisines=["chinese"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.75, rating=4.1)),
            ActivityItem(name="Pasta Paradise Italian", category="dining", cost=20, duration=60,
                attributes=ActivityAttributes(cuisines=["italian"], vibes=["romantic", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.78, rating=4.2)),
            ActivityItem(name="Taco Fiesta Mexican", category="dining", cost=14, duration=50,
                attributes=ActivityAttributes(cuisines=["mexican"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.70, rating=4.0)),
            ActivityItem(name="Thai Orchid Garden", category="dining", cost=17, duration=55,
                attributes=ActivityAttributes(cuisines=["thai"], vibes=["social", "cultural"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.72, rating=4.1)),
            ActivityItem(name="Sushi Master Japanese", category="dining", cost=25, duration=60,
                attributes=ActivityAttributes(cuisines=["japanese"], vibes=["luxurious", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Dosa Plaza South Indian", category="dining", cost=8, duration=40,
                attributes=ActivityAttributes(cuisines=["south_indian", "vegetarian"], vibes=["budget_friendly", "family_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.80, rating=4.2)),
            ActivityItem(name="BBQ Nation Grill House", category="dining", cost=22, duration=90,
                attributes=ActivityAttributes(cuisines=["american", "indian"], vibes=["social", "family_friendly"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.88, rating=4.4)),
            ActivityItem(name="Green Bowl Vegan Cafe", category="dining", cost=15, duration=45,
                attributes=ActivityAttributes(cuisines=["vegan", "vegetarian", "mediterranean"], vibes=["budget_friendly", "social"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.65, rating=4.3)),
            ActivityItem(name="Chai & Snacks Corner", category="dining", cost=4, duration=30,
                attributes=ActivityAttributes(cuisines=["indian"], vibes=["budget_friendly", "social"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.75, rating=4.0)),
            ActivityItem(name="Fine Dining at The Grand", category="dining", cost=50, duration=90,
                attributes=ActivityAttributes(cuisines=["continental", "mediterranean"], vibes=["luxurious", "romantic"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.92, rating=4.7)),
            ActivityItem(name="Korean BBQ House", category="dining", cost=20, duration=75,
                attributes=ActivityAttributes(cuisines=["korean"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.78, rating=4.3)),
            ActivityItem(name="Free Community Kitchen", category="dining", cost=0, duration=40,
                attributes=ActivityAttributes(cuisines=["indian", "vegetarian"], vibes=["budget_friendly", "cultural"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.60, rating=4.0)),
            ActivityItem(name="Street Food Junction", category="dining", cost=5, duration=35,
                attributes=ActivityAttributes(cuisines=["indian"], vibes=["budget_friendly", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.82, rating=4.1)),
            ActivityItem(name="Seafood Paradise", category="dining", cost=22, duration=60,
                attributes=ActivityAttributes(cuisines=["seafood", "indian"], vibes=["social", "luxurious"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.80, rating=4.4)),
        ]
        if cuisines:
            sample_restaurants = [r for r in sample_restaurants 
                                 if any(c in r.attributes.cuisines for c in cuisines)]
        sample_restaurants = [r for r in sample_restaurants if r.cost <= max_cost]
        for r in sample_restaurants:
            if r.cost <= 5: r.cost = 150
            elif r.cost <= 15: r.cost = 600
            elif r.cost <= 30: r.cost = 1200
            else: r.cost = 2500
            r.lat = 0.001 * random.uniform(-20, 20)
            r.lon = 0.001 * random.uniform(-20, 20)
        return sample_restaurants
    
    def _get_sample_events(self, location: str, event_type: str) -> List[ActivityItem]:
        sample_events = [
            ActivityItem(name="Live Music Night at Blue Note", category="entertainment", cost=15, duration=120,
                attributes=ActivityAttributes(genres=["music"], vibes=["social", "entertaining"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Comedy Night - Stand Up Special", category="entertainment", cost=18, duration=90,
                attributes=ActivityAttributes(genres=["comedy"], vibes=["entertaining", "social"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.80, rating=4.3)),
            ActivityItem(name="Art Gallery Exhibition Opening", category="cultural", cost=10, duration=90,
                attributes=ActivityAttributes(vibes=["cultural", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.65, rating=4.2)),
            ActivityItem(name="Escape Room Adventure", category="entertainment", cost=24, duration=70,
                attributes=ActivityAttributes(vibes=["adventurous", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.88, rating=4.6)),
            ActivityItem(name="Bowling Night at Strike Zone", category="entertainment", cost=16, duration=90,
                attributes=ActivityAttributes(vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.82, rating=4.1)),
            ActivityItem(name="Jazz Lounge Evening", category="entertainment", cost=20, duration=120,
                attributes=ActivityAttributes(genres=["music"], vibes=["relaxing", "romantic"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.75, rating=4.4)),
            ActivityItem(name="Free Outdoor Concert", category="entertainment", cost=0, duration=150,
                attributes=ActivityAttributes(genres=["music"], vibes=["social", "budget_friendly"],
                    time_slots=["evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.90, rating=4.3)),
            ActivityItem(name="Theatre Play - The Last Act", category="cultural", cost=25, duration=150,
                attributes=ActivityAttributes(genres=["drama"], vibes=["cultural", "social"],
                    time_slots=["evening"], suitable_for_groups=True, indoor_outdoor="indoor",
                    booking_required=True, popularity_score=0.70, rating=4.5)),
            ActivityItem(name="Karaoke Night", category="entertainment", cost=12, duration=120,
                attributes=ActivityAttributes(vibes=["social", "entertaining"],
                    time_slots=["evening", "night"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.78, rating=4.0)),
            ActivityItem(name="Museum Special Exhibition", category="cultural", cost=12, duration=120,
                attributes=ActivityAttributes(vibes=["cultural", "educational"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="indoor",
                    popularity_score=0.68, rating=4.4)),
        ]
        for e in sample_events:
            if e.cost <= 5: e.cost = 0
            elif e.cost <= 15: e.cost = 400
            elif e.cost <= 30: e.cost = 1000
            else: e.cost = 2500
            e.lat = 0.001 * random.uniform(-20, 20)
            e.lon = 0.001 * random.uniform(-20, 20)
        return sample_events
    
    def _get_sample_outdoor(self, location: str, activity_type: str) -> List[ActivityItem]:
        sample_relaxed = [
            ActivityItem(name="Central Park Stroll", category="outdoor_relaxed", cost=0, duration=90,
                attributes=ActivityAttributes(vibes=["relaxing", "budget_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Botanical Garden Visit", category="outdoor_relaxed", cost=5, duration=90,
                attributes=ActivityAttributes(vibes=["relaxing", "cultural"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.75, rating=4.3)),
            ActivityItem(name="Sunset Beach Walk", category="outdoor_relaxed", cost=0, duration=60,
                attributes=ActivityAttributes(vibes=["relaxing", "romantic"],
                    time_slots=["evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.90, rating=4.7)),
            ActivityItem(name="Lake Viewpoint Picnic", category="outdoor_relaxed", cost=0, duration=120,
                attributes=ActivityAttributes(vibes=["relaxing", "family_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.80, rating=4.4)),
            ActivityItem(name="Heritage Walking Trail", category="outdoor_relaxed", cost=0, duration=90,
                attributes=ActivityAttributes(vibes=["cultural", "budget_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.70, rating=4.2)),
        ]
        sample_active = [
            ActivityItem(name="Adventure Trek Base Camp", category="outdoor_active", cost=25, duration=180,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.82, rating=4.5)),
            ActivityItem(name="Rock Climbing Center", category="outdoor_active", cost=28, duration=120,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.78, rating=4.3)),
            ActivityItem(name="Kayaking & Water Sports", category="outdoor_active", cost=22, duration=120,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.85, rating=4.6)),
            ActivityItem(name="Go-Kart Racing Arena", category="outdoor_active", cost=20, duration=60,
                attributes=ActivityAttributes(vibes=["adventurous", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.88, rating=4.4)),
            ActivityItem(name="Cycling Trail Adventure", category="outdoor_active", cost=10, duration=120,
                attributes=ActivityAttributes(vibes=["active", "budget_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.75, rating=4.2)),
            ActivityItem(name="Paintball Combat Zone", category="outdoor_active", cost=28, duration=90,
                attributes=ActivityAttributes(vibes=["adventurous", "social"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.80, rating=4.3)),
            ActivityItem(name="Horseback Riding Stables", category="outdoor_active", cost=35, duration=90,
                attributes=ActivityAttributes(vibes=["adventurous", "relaxing"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.72, rating=4.4)),
            ActivityItem(name="Public Sports Ground", category="outdoor_active", cost=0, duration=90,
                attributes=ActivityAttributes(vibes=["active", "budget_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True, indoor_outdoor="outdoor",
                    popularity_score=0.85, rating=4.1)),
        ]
        for o in sample_relaxed + sample_active:
            if o.cost == 0: pass
            elif o.cost <= 10: o.cost = 200
            elif o.cost <= 25: o.cost = 800
            else: o.cost = 1500
            o.lat = 0.001 * random.uniform(-20, 20)
            o.lon = 0.001 * random.uniform(-20, 20)
        if activity_type == "outdoor_relaxed":
            return sample_relaxed
        elif activity_type == "outdoor_active":
            return sample_active
        else:
            return sample_relaxed + sample_active

import time

class PreferenceMatcher:
    def __init__(self):
        self.genre_embeddings = self._build_genre_similarity()
        self.cuisine_embeddings = self._build_cuisine_similarity()
    
    def _build_genre_similarity(self) -> Dict[str, Dict[str, float]]:
        similar = {
            "action": {"adventure": 0.9, "thriller": 0.7, "sci-fi": 0.6, "fantasy": 0.5},
            "romance": {"family": 0.8, "drama": 0.7, "animation": 0.6},
            "drama": {"thriller": 0.6, "romance": 0.5, "mystery": 0.5},
            "horror": {"thriller": 0.9, "mystery": 0.6},
            "comedy": {"drama": 0.7, "romance": 0.6},
            "mystery": {"thriller": 0.8, "horror": 0.7, "action": 0.6},
            "sci-fi": {"action": 0.7, "adventure": 0.8, "fantasy": 0.6},
            "animation": {"family": 0.9, "comedy": 0.7, "adventure": 0.6},
            "documentary": {"drama": 0.4},
            "family": {"animation": 0.9, "comedy": 0.7, "adventure": 0.6},
            "fantasy": {"action": 0.8, "sci-fi": 0.7, "adventure": 0.8, "family": 0.6},
            "thriller": {"mystery": 0.8, "horror": 0.5, "drama": 0.5},
            "adventure": {"action": 0.9, "sci-fi": 0.6, "fantasy": 0.5},
        }
        return similar
    
    def _build_cuisine_similarity(self) -> Dict[str, Dict[str, float]]:
        similar = {
            "indian": {"north_indian": 0.95, "south_indian": 0.85},
            "north_indian": {"indian": 0.95, "mughlai": 0.8},
            "south_indian": {"indian": 0.85},
            "chinese": {"korean": 0.5, "japanese": 0.4},
            "thai": {"korean": 0.6, "chinese": 0.4},
            "italian": {"mediterranean": 0.7, "continental": 0.5},
            "mediterranean": {"italian": 0.7, "continental": 0.6},
            "american": {"continental": 0.4},
            "vietnamese": {"chinese": 0.4, "thai": 0.6},
            "korean": {"thai": 0.6, "chinese": 0.4},
            "japanese": {"korean": 0.6, "chinese": 0.5},
            "continental": {"japanese": 0.5, "mediterranean": 0.4},
            "vegetarian": {"vegan": 0.9, "indian": 0.6},
            "vegan": {"vegetarian": 0.9},
        }
        return similar
    
    def compute_genre_match(self, preferred_genres: List[str], item_genres: List[str]) -> float:
        if not preferred_genres or not item_genres:
            return 0.5
        max_score = 0.0
        for pref_g in preferred_genres:
            for item_g in item_genres:
                if pref_g == item_g:
                    max_score = max(max_score, 1.0)
                elif pref_g in self.genre_embeddings:
                    max_score = max(max_score, 
                                   self.genre_embeddings[pref_g].get(item_g, 0.0))
        return max_score
    
    def compute_cuisine_match(self, preferred_cuisines: List[str], item_cuisines: List[str]) -> float:
        if not preferred_cuisines or not item_cuisines:
            return 0.5
        max_score = 0.0
        for pref_c in preferred_cuisines:
            for item_c in item_cuisines:
                if pref_c == item_c:
                    max_score = max(max_score, 1.0)
                elif pref_c in self.cuisine_embeddings:
                    max_score = max(max_score,
                                   self.cuisine_embeddings[pref_c].get(item_c, 0.0))
        return max_score
    
    def compute_vibe_match(self, preferred_vibes: List[str], item_vibes: List[str]) -> float:
        if not preferred_vibes or not item_vibes:
            return 0.5
        common = len(set(preferred_vibes) & set(item_vibes))
        return common / max(len(preferred_vibes), 1)
    
    def compute_time_match(self, time_slot: str, item_time_slots: List[str]) -> float:
        if not item_time_slots:
            return 0.7
        if time_slot in item_time_slots:
            return 1.0
        adjacent = {
            "morning": ["afternoon"],
            "afternoon": ["morning", "evening"],
            "evening": ["afternoon", "night"],
            "night": ["evening", "late_night"],
            "late_night": ["night"],
        }
        for adj in adjacent.get(time_slot, []):
            if adj in item_time_slots:
                return 0.7
        return 0.3

class GroupPreferenceAggregator:
    def __init__(self):
        self.matcher = PreferenceMatcher()
    
    def aggregate_preferences(self, member_preferences: List[Dict]) -> Dict:
        if not member_preferences:
            return {
                "genres": [],
                "cuisines": [],
                "vibes": ["social"],
                "budget_range": "medium",
                "indoor_outdoor": "both",
                "preferred_time_slots": ["afternoon", "evening"],
                "dietary_restrictions": [],
                "energy_level": 3,
            }
        genre_votes = defaultdict(int)
        cuisine_votes = defaultdict(int)
        vibe_votes = defaultdict(int)
        budget_votes = defaultdict(int)
        indoor_outdoor_votes = defaultdict(int)
        time_slot_votes = defaultdict(int)
        dietary_votes = defaultdict(int)
        energy_levels = []
        exploration_factors = []
        for pref in member_preferences:
            for g in pref.get("genres", []):
                genre_votes[g.lower().replace("-", "")] += 1
            for c in pref.get("cuisines", []):
                cuisine_votes[c.lower().replace(" ", "_")] += 1
            for v in pref.get("vibes", []):
                vibe_votes[v.lower().replace("-", "_")] += 1
            budget = pref.get("budget_range", "medium")
            budget_votes[budget] += 1
            io = pref.get("indoor_outdoor", "both")
            indoor_outdoor_votes[io] += 1
            for t in pref.get("preferred_time_slots", []):
                time_slot_votes[t.lower()] += 1
            for d in pref.get("dietary_restrictions", []):
                dietary_votes[d.lower()] += 1
            if pref.get("energy_level"):
                energy_levels.append(pref["energy_level"])
            if pref.get("exploration_factor"):
                exploration_factors.append(float(pref["exploration_factor"]))
        n_members = len(member_preferences)
        threshold = n_members / 3
        def top_items(votes: Dict, min_votes: int = 1) -> List[str]:
            sorted_items = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            return [item for item, count in sorted_items if count >= min_votes][:5]
        sorted_budgets = sorted(budget_votes.items(), key=lambda x: x[1], reverse=True)
        budget = sorted_budgets[0][0] if sorted_budgets else "medium"
        budget_order = ["free", "low", "medium", "high"]
        budget_idx = budget_order.index(budget)
        for b, count in sorted_budgets:
            idx = budget_order.index(b)
            if count >= n_members / 2:
                budget_idx = min(budget_idx, idx)
                break
        budget = budget_order[budget_idx]
        io_sorted = sorted(indoor_outdoor_votes.items(), key=lambda x: x[1], reverse=True)
        indoor_outdoor = io_sorted[0][0] if io_sorted else "both"
        if io_sorted and io_sorted[0][1] < n_members / 2:
            indoor_outdoor = "both"
        avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 3
        avg_exploration = sum(exploration_factors) / len(exploration_factors) if exploration_factors else 1.5
        dietary = list(dietary_votes.keys())
        def compute_borda(votes_list: List[List[str]], all_options: Set[str]):
            scores = defaultdict(float)
            for votes in votes_list:
                n_user_prefs = len(votes)
                for i, item in enumerate(votes):
                    item_clean = item.lower().replace("-", "").replace(" ", "_")
                    scores[item_clean] += (n_user_prefs - i)
            return scores
        def top_borda(scores: Dict[str, float], n: int = 4):
            sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return [k for k, v in sorted_items[:n] if v > 0]
        genre_pref_list = [p.get("genres", []) for p in member_preferences]
        cuisine_pref_list = [p.get("cuisines", []) for p in member_preferences]
        vibe_pref_list = [p.get("vibes", []) for p in member_preferences]
        time_pref_list = [p.get("preferred_time_slots", []) for p in member_preferences]
        genre_scores = compute_borda(genre_pref_list, set())
        cuisine_scores = compute_borda(cuisine_pref_list, set())
        vibe_scores = compute_borda(vibe_pref_list, set())
        time_scores = compute_borda(time_pref_list, set())
        res_genres = top_borda(genre_scores, 5)
        res_cuisines = top_borda(cuisine_scores, 5)
        res_vibes = top_borda(vibe_scores, 3)
        res_times = top_borda(time_scores, 2) or ["afternoon", "evening"]
        return {
            "genres": res_genres,
            "cuisines": res_cuisines,
            "vibes": res_vibes,
            "budget_range": budget,
            "indoor_outdoor": indoor_outdoor,
            "preferred_time_slots": res_times,
            "dietary_restrictions": dietary,
            "exploration_factor": avg_exploration,
            "energy_level": round(avg_energy, 1),
            "member_count": n_members,
        }

class ThompsonSamplingArm:
    def __init__(self, d: int = FEATURE_DIM, v: float = 0.5):
        self.d = d
        self.v = v
        self.B_inv = np.eye(d, dtype=np.float64)
        self.f = np.zeros(d, dtype=np.float64)
        self.mu = np.zeros(d, dtype=np.float64)
        self._lock = threading.Lock()

    def sample_score(self, x: np.ndarray) -> float:
        with self._lock:
            eps = np.random.normal(0, self.v, self.d)
            theta_sample = self.mu + (self.B_inv @ eps)
            return float(theta_sample @ x)

    def update(self, x: np.ndarray, reward: float):
        with self._lock:
            Bx = self.B_inv @ x
            denom = 1.0 + float(x @ Bx)
            if denom > 1e-10:
                self.B_inv -= np.outer(Bx, Bx) / denom
            self.f += reward * x
            self.mu = self.B_inv @ self.f

    def to_dict(self) -> Dict:
        with self._lock:
            return {
                "d": self.d, "v": self.v,
                "B_inv": self.B_inv.tolist(),
                "f": self.f.tolist(),
                "mu": self.mu.tolist()
            }

    @classmethod
    def from_dict(cls, data: Dict) -> "ThompsonSamplingArm":
        arm = cls(data["d"], data["v"])
        arm.B_inv = np.array(data["B_inv"], dtype=np.float64)
        arm.f = np.array(data["f"], dtype=np.float64)
        arm.mu = np.array(data["mu"], dtype=np.float64)
        return arm

class ContentBasedScorer:
    def __init__(self, actions: List[str]):
        self.actions = actions
        self.category_vectors = {
            "dining": np.array([1, 0, 0, 0, 1]),
            "movie": np.array([0, 1, 0, 0, 0]),
            "outdoor_relaxed": np.array([0, 0, 1, 1, 0]),
            "outdoor_active": np.array([0, 0, 1, 1, 1]),
            "cultural": np.array([1, 1, 0, 0, 0]),
            "entertainment": np.array([0, 1, 1, 0, 1])
        }

    def compute_similarity(self, item: ActivityItem, user_pref_vector: np.ndarray) -> float:
        item_vec = self.category_vectors.get(item.category, np.zeros(5))
        if "social" in item.attributes.vibes: item_vec[0] += 0.5
        if "cultural" in item.attributes.vibes: item_vec[1] += 0.5
        norm_i = np.linalg.norm(item_vec)
        norm_u = np.linalg.norm(user_pref_vector)
        if norm_i == 0 or norm_u == 0: return 0.5
        return np.dot(item_vec, user_pref_vector) / (norm_i * norm_u)

class ContextualThompsonEngine:
    def __init__(self, db=None, alpha: float = 1.0):
        self.db = db
        self.actions = ACTIONS
        self.rl_arms: Dict[str, ThompsonSamplingArm] = {
            a: ThompsonSamplingArm(FEATURE_DIM) for a in self.actions
        }
        self.content_scorer = ContentBasedScorer(self.actions)
        self.matcher = PreferenceMatcher()
        
    def set_alpha(self, alpha: float):
        v = alpha / 3.0
        for arm in self.rl_arms.values():
            arm.v = v

    def score_item(self, item: ActivityItem, context: Dict, group_prefs: Dict) -> float:
        bandit_context = self._build_context_features(context)
        rl_score = self.rl_arms[item.category].sample_score(bandit_context)
        genre_match = self.matcher.compute_genre_match(group_prefs.get("genres", []), item.attributes.genres)
        cuisine_match = self.matcher.compute_cuisine_match(group_prefs.get("cuisines", []), item.attributes.cuisines)
        vibe_match = self.matcher.compute_vibe_match(group_prefs.get("vibes", []), item.attributes.vibes)
        time_slot = context.get("time_slot", "afternoon")
        time_match = self.matcher.compute_time_match(time_slot, item.attributes.time_slots)
        collab_signal = item.attributes.popularity_score
        attribute_score = (
            genre_match * 0.25 +
            cuisine_match * 0.25 +
            vibe_match * 0.2 +
            time_match * 0.15 +
            (collab_signal * 0.15)
        )
        rl_norm = 1.0 / (1.0 + np.exp(-rl_score))
        final_score = (rl_norm * 0.45) + (attribute_score * 0.55)
        return float(final_score)

    def score_action(self, action: str, context: Dict) -> float:
        if action not in self.rl_arms:
            return 0.0
        return self.rl_arms[action].sample_score(self._build_context_features(context))

    def update(self, action: str, context: Dict, reward: float):
        if action in self.rl_arms:
            features = self._build_context_features(context)
            self.rl_arms[action].update(features, reward)

    def rank_items(self, items: List[ActivityItem], context: Dict,
                   group_prefs: Dict) -> List[Tuple[ActivityItem, float]]:
        scored = [(item, self.score_item(item, context, group_prefs)) for item in items]
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def get_state(self) -> Dict:
        return {a: arm.to_dict() for a, arm in self.rl_arms.items()}
    
    def load_state(self, state: Dict):
        for a, d in state.items():
            if a in self.rl_arms:
                try:
                    self.rl_arms[a] = ThompsonSamplingArm.from_dict(d)
                except Exception:
                    pass

    def _build_context_features(self, context: Dict) -> np.ndarray:
        b_map = {"free": 0.0, "low": 0.25, "medium": 0.5, "high": 1.0}
        b = b_map.get(context.get("budget", "medium"), 0.5)
        h = int(context.get("time_minutes", 720)) // 60
        pref = context.get("indoor_outdoor", "both")
        ws = float(context.get("weather_score", 0.7))
        gs = min(int(context.get("group_size", 2)), 10) / 10.0
        dp = float(context.get("day_progress", 0.5))
        div = float(context.get("diversity_penalty", 0.0))
        iw = 1.0 if context.get("is_weekend", False) else 0.0
        genre_match = float(context.get("genre_match", 0.5))
        cuisine_match = float(context.get("cuisine_match", 0.5))
        vibe_match = float(context.get("vibe_match", 0.5))
        time_match = float(context.get("time_match", 0.7))
        br = float(context.get("budget_ratio", 0.0))
        tsm = min(float(context.get("time_since_meal", 240)), 480.0) / 480.0
        return np.array([
            b,
            ws,
            gs,
            dp,
            div,
            iw,
            br,
            tsm,
            genre_match,
            cuisine_match,
            vibe_match,
            time_match,
            1.0 if pref in ("outdoor", "both") else 0.0,
            1.0 if pref in ("indoor", "both") else 0.0,
            1.0 if 5 <= h < 12 else 0.0,
            1.0 if 12 <= h < 17 else 0.0,
            1.0 if 17 <= h < 21 else 0.0,
            1.0 if h >= 21 or h < 5 else 0.0,
            1.0 if 5 <= h < 12 else 0.0,
            1.0 if 12 <= h < 17 else 0.0,
            1.0 if 17 <= h < 21 else 0.0,
            1.0,
        ], dtype=np.float64)

class GeoEngine:
    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        try:
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
                 * math.sin(dlon / 2) ** 2)
            return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_centroid(locations: List[Dict]) -> Tuple[float, float]:
        valid = [l for l in locations
                 if isinstance(l, dict) and l.get("lat") and l.get("lon")
                 and float(l["lat"]) != 0.0 and float(l["lon"]) != 0.0]
        if not valid:
            return 16.5062, 80.6480
        x = y = z = 0.0
        for loc in valid:
            la = math.radians(float(loc["lat"]))
            lo = math.radians(float(loc["lon"]))
            x += math.cos(la) * math.cos(lo)
            y += math.cos(la) * math.sin(lo)
            z += math.sin(la)
        n = len(valid)
        x /= n; y /= n; z /= n
        return (
            math.degrees(math.atan2(z, math.sqrt(x * x + y * y))),
            math.degrees(math.atan2(y, x))
        )

class BeamNode:
    def __init__(
        self,
        current_time: int,
        schedule: List[Dict],
        spent: float,
        score: float,
        diversity: Dict[str, int],
        exclusion: set,
        last_meal_time: int = 0
    ):
        self.current_time = current_time
        self.schedule = schedule
        self.spent = spent
        self.score = score
        self.diversity = diversity
        self.exclusion = exclusion
        self.last_meal_time = last_meal_time

    def clone(self):
        return BeamNode(
            self.current_time,
            list(self.schedule),
            self.spent,
            self.score,
            dict(self.diversity),
            set(self.exclusion),
            self.last_meal_time
        )

class ItineraryBuilder:
    def __init__(self, bandit: ContextualThompsonEngine):
        self.bandit = bandit
        self.matcher = PreferenceMatcher()
    
    def _travel_time(self, dist_km: float) -> int:
        if dist_km <= 0.1:
            return 0
        return max(5, int((dist_km / TRAVEL_SPEED_KMH) * 60))
    
    def _get_time_slot(self, minutes: int) -> str:
        h = minutes // 60
        if 5 <= h < 12:
            return "morning"
        elif 12 <= h < 17:
            return "afternoon"
        elif 17 <= h < 21:
            return "evening"
        else:
            return "night"
    
    def build(
        self,
        pool: Dict[str, List[ActivityItem]],
        context: Dict,
        start_min: int,
        end_min: int,
        centroid: Tuple[float, float],
        group_prefs: Dict,
        exclusion_set: set,
    ) -> List[Dict]:
        max_spend = float(MAX_BUDGET_MAP.get(context.get("budget", "medium"), 1500))
        span = max(end_min - start_min, 1)
        
        logger.info(
            f"[ItineraryBuilder] Building for {start_min}-{end_min}, budget={max_spend}"
        )

        root = BeamNode(
            current_time=start_min,
            schedule=[],
            spent=0.0,
            score=0.0,
            diversity={},
            exclusion=set(exclusion_set),
            last_meal_time=start_min
        )
        
        beam = [root]
        beam_width = 5
        final_itineraries = []

        for step in range(12):
            new_candidates = []
            
            for node in beam:
                
                if node.current_time >= end_min:
                    final_itineraries.append(node)
                    continue

                time_slot = self._get_time_slot(node.current_time)
                dp = (node.current_time - start_min) / span

                budget_ratio = node.spent / (max_spend + 1)
                time_since_meal = node.current_time - node.last_meal_time
                
                time_context = {
                    **context,
                    "time_minutes": node.current_time,
                    "day_progress": dp,
                    "time_slot": time_slot,
                    "budget_ratio": budget_ratio,
                    "time_since_meal": time_since_meal
                }

                found_step = False
                for category, items in pool.items():
                    if not items: continue

                    div_count = node.diversity.get(category, 0)
                    diversity_penalty = (div_count**2) * 2.0
                    
                    if node.schedule and node.schedule[-1]["category"] == category:
                        diversity_penalty += 10.0
                    
                    for item in items:
                        if item.name in node.exclusion: continue

                        if max_spend > 0 and node.spent + item.cost > max_spend * 1.15:
                            continue

                        lat = item.lat if item.lat != 0.0 else centroid[0]
                        lon = item.lon if item.lon != 0.0 else centroid[1]
                        dist = GeoEngine.haversine(centroid[0], centroid[1], lat, lon)
                        travel = self._travel_time(dist)
                        
                        if node.current_time + travel + item.duration > end_min:
                            continue

                        base_score = self.bandit.score_item(item, time_context, group_prefs)

                        dist_penalty = dist / 15.0

                        budget_tier = context.get("budget", "medium")
                        if budget_tier in ["medium", "high"]:
                            cost_score = (item.cost / max_spend) * 0.5
                        else:
                            cost_score = -(item.cost / (max_spend + 1)) * 0.5

                        time_match = self.matcher.compute_time_match(time_slot, item.attributes.time_slots)

                        seq_bonus = 0.0
                        if category == "dining":
                            if node.schedule and node.schedule[-1]["category"] != "dining":
                                seq_bonus += 1.0
                            arrival_h = (node.current_time + travel) // 60
                            if 12 <= arrival_h <= 14:
                                if time_since_meal > 180:
                                    seq_bonus += 15.0
                            elif 19 <= arrival_h <= 21:
                                if time_since_meal > 240:
                                    seq_bonus += 15.0
                            elif time_since_meal > 240:
                                seq_bonus += 3.0
                        
                        total_score = base_score + seq_bonus + cost_score - dist_penalty - diversity_penalty

                        if time_match < 0.3:
                            continue

                        new_node = node.clone()
                        arrival = node.current_time + travel
                        departure = arrival + item.duration
                        
                        arrival_time_str = f"{arrival // 60:02d}:{arrival % 60:02d}"
                        departure_time_str = f"{departure // 60:02d}:{departure % 60:02d}"
                        
                        entry = {
                            **item.to_dict(),
                            "activity_name": item.name,
                            "display_name": item.name,
                            "arrival_time": arrival_time_str,
                            "departure_time": departure_time_str,
                            "time_slot_display": f"{arrival_time_str} - {departure_time_str}",
                            "estimated_duration": item.duration,
                            "estimated_cost": item.cost,
                            "distance_km": round(dist, 2),
                            "travel_time_min": travel,
                            "score": total_score
                        }
                        
                        new_node.schedule.append(entry)
                        new_node.exclusion.add(item.name)
                        new_node.current_time = arrival + item.duration
                        new_node.spent += item.cost
                        new_node.diversity[category] = div_count + 1
                        new_node.score += total_score
                        
                        if category == "dining":
                            new_node.last_meal_time = new_node.current_time
                        
                        new_candidates.append(new_node)
                        found_step = True

                if not found_step:
                    final_itineraries.append(node)

            if not new_candidates:
                break

            new_candidates.sort(key=lambda x: x.score, reverse=True)
            beam = new_candidates[:beam_width]

        if not final_itineraries and not beam:
            return []
            
        all_final = final_itineraries + beam
        best_overall = max(all_final, key=lambda x: x.score)
        
        logger.info(
            f"[ItineraryBuilder] Best itinerary: {len(best_overall.schedule)} items, score={best_overall.score:.2f}"
        )
        
        return best_overall.schedule

class WeatherFetcher:
    async def score(self, lat: float, lon: float) -> float:
        try:
            url = (f"https://api.open-meteo.com/v1/forecast"
                   f"?latitude={lat}&longitude={lon}&current_weather=true")
            async with httpx.AsyncClient(timeout=7.0) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                code = int(resp.json().get("current", {}).get("weathercode", 0))
                mapping = {0: 1.0, 1: 0.85, 2: 0.80, 3: 0.65, 45: 0.50, 48: 0.50}
                if code in mapping:
                    return mapping[code]
                if 51 <= code <= 67:
                    return 0.30
                if 71 <= code <= 77:
                    return 0.15
                if 80 <= code <= 82:
                    return 0.40
                if code in (95, 96, 99):
                    return 0.10
        except Exception:
            pass
        return 0.70

class HybridRecommendationEngine:
    def __init__(self, db):
        self.db = db
        self.bandit = ContextualThompsonEngine(self.db)
        self.builder = ItineraryBuilder(self.bandit)
        self.weather = WeatherFetcher()
        self.web_fetcher = WebDataFetcher()
        self.pref_aggregator = GroupPreferenceAggregator()
        self._llm = None
    
    async def initialize(self):
        try:
            doc = await self.db.rl_model_state.find_one({"model_type": "thompson"})
            if doc and "arms" in doc:
                self.bandit.load_state(doc["arms"])
                logger.info("Thompson Sampling model state loaded from database")
        except Exception as exc:
            logger.warning(f"Could not load RL model: {exc}")
    
    async def _save_model(self):
        try:
            await self.db.rl_model_state.update_one(
                {"model_type": "thompson"},
                {"$set": {
                    "model_type": "thompson",
                    "arms": self.bandit.get_state(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning(f"Could not save RL model: {exc}")
    
    async def _geocode(self, name: str) -> Optional[Tuple[float, float]]:
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": name, "format": "json", "limit": 1},
                    headers={"User-Agent": "GroupSyncApp/3.0"},
                )
            if resp.status_code == 200 and resp.json():
                d = resp.json()[0]
                return float(d["lat"]), float(d["lon"])
        except Exception:
            pass
        return None
    
    async def _reverse_geocode(self, lat: float, lon: float) -> str:
        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    params={"format": "jsonv2", "lat": lat, "lon": lon},
                    headers={"User-Agent": "GroupSyncApp/3.0"},
                )
            if resp.status_code == 200:
                addr = resp.json().get("address", {})
                return (
                    addr.get("city") or
                    addr.get("town") or
                    addr.get("state") or
                    "Your City"
                )
        except Exception:
            pass
        return "Your City"
    
    def _parse_time(self, t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        except Exception:
            return 0
    
    async def _fetch_activities(
        self,
        lat: float,
        lon: float,
        categories: List[str],
        group_prefs: Dict,
    ) -> Dict[str, List[ActivityItem]]:
        pool: Dict[str, List[ActivityItem]] = {cat: [] for cat in ACTIONS}
        
        fetch_tasks = []
        
        if "dining" in categories:
            fetch_tasks.append(self.web_fetcher.search_restaurants(
                lat, lon, group_prefs.get("cuisines", []), 
                group_prefs.get("budget_range", "medium")
            ))
        
        if "movie" in categories:
            fetch_tasks.append(self.web_fetcher.search_movies(
                lat, lon, group_prefs.get("genres", [])
            ))
        
        if "entertainment" in categories:
            fetch_tasks.append(self.web_fetcher.search_events(
                lat, lon, "entertainment"
            ))
        
        if "cultural" in categories:
            fetch_tasks.append(self.web_fetcher.search_events(
                lat, lon, "cultural"
            ))
        
        if "outdoor_relaxed" in categories:
            fetch_tasks.append(self.web_fetcher.search_outdoor_activities(
                lat, lon, "outdoor_relaxed", group_prefs.get("vibes", [])
            ))
        
        if "outdoor_active" in categories:
            fetch_tasks.append(self.web_fetcher.search_outdoor_activities(
                lat, lon, "outdoor_active", group_prefs.get("vibes", [])
            ))

        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        idx = 0
        for cat in ACTIONS:
            if cat in categories and idx < len(results):
                result = results[idx]
                if isinstance(result, list) and len(result) > 0:
                    pool[cat] = [item for item in result if item.source != "sample"]
                    if not pool[cat]: 
                         pool[cat] = result
                elif isinstance(result, Exception) or (isinstance(result, list) and len(result) == 0):
                    logger.warning(f"Fetch failed or empty for {cat}. Using sample data as fallback.")
                    pool[cat] = self._get_sample_for_category(cat, group_prefs)
                idx += 1
            elif cat in categories:
                pool[cat] = self._get_sample_for_category(cat, group_prefs)

        for cat, items in pool.items():
            if items:
                logger.info(f"[Pool] {cat}: {len(items)} items")
        
        return pool
    
    def _get_sample_for_category(self, category: str, group_prefs: Dict) -> List[ActivityItem]:
        if category == "dining":
            return self.web_fetcher._get_sample_restaurants(
                "local", group_prefs.get("cuisines", []),
                group_prefs.get("budget_range", "medium")
            )
        elif category == "movie":
            return self.web_fetcher._get_sample_movies(
                "local", group_prefs.get("genres", [])
            )
        elif category in ("entertainment", "cultural"):
            return self.web_fetcher._get_sample_events("local", category)
        else:
            return self.web_fetcher._get_sample_outdoor("local", category)
    
    async def _llm_summary(
        self, schedule: List[Dict], city: str, constraints: Dict, group_prefs: Dict
    ) -> Tuple[str, str]:
        if not schedule:
            return (
                "No activities could be scheduled. Try adjusting your time or preferences.",
                "Insufficient data or constraints too tight to generate a valid itinerary."
            )

        llm = self._get_llm()
        if not llm:
            return self._generate_fallback_summary(schedule, city, group_prefs)
        
        lines = "\n".join(
            f"{i+1}. {s['name']} ({s['type']}, {s['duration']}min, Rs.{s.get('estimated_cost', 0)})"
            for i, s in enumerate(schedule[:14])
        )

        prompt = (
            f"Given this group itinerary for {city}:\n{lines}\n"
            f"Constraints: {json.dumps(constraints, default=str)}\n"
            f"Group prefs: {json.dumps(group_prefs, default=str)}\n"
            f"Return JSON with 'summary' (2-3 sentences, engaging) and 'reasoning' (why these choices)."
        )
        
        for i in range(3): 
            try:
                resp = await llm.chat.completions.create(
                    model="z-ai/glm-4.5-air:free",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    timeout=15.0,
                )
                data = json.loads(resp.choices[0].message.content)
                return data.get("summary", ""), data.get("reasoning", "")
            except Exception as exc:
                if i < 2:
                    await asyncio.sleep(1 + random.random())
                else:
                    logger.warning(f"LLM summary failed after 3 attempts: {exc}")
        
        return self._generate_fallback_summary(schedule, city, group_prefs)
    
    def _generate_fallback_summary(self, schedule: List[Dict], city: str, group_prefs: Dict) -> Tuple[str, str]:
        cats = sorted({s["type"] for s in schedule})
        total_cost = sum(float(s.get("estimated_cost", 0)) for s in schedule)
        return (
            f"Your {len(schedule)}-activity plan in {city} covers {', '.join(cats)}. "
            f"Total estimated cost: Rs.{total_cost:.0f}.",
            f"Selected {len(schedule)} diverse activities matching group preferences for {', '.join(cats)}."
        )
    
    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        try:
            from openai import AsyncOpenAI as _OAI
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if key:
                self._llm = _OAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=key,
                )
                return self._llm
        except ImportError:
            pass
        return None
    
    async def generate_recommendation(
        self, group_id: str, adjustment_context: Optional[str] = None
    ) -> Dict[str, Any]:
        group = await self.db.group_sessions.find_one({"id": group_id}, {"_id": 0})
        if not group:
            raise ValueError("Group not found")
        
        constraints = group.get("constraints", {})
        start_min = self._parse_time(constraints.get("start_time", "09:00"))
        end_min = self._parse_time(constraints.get("end_time", "21:00"))
        budget = constraints.get("budget_range", "medium")
        pref = constraints.get("indoor_outdoor", "both")
        is_vac = bool(constraints.get("is_vacation", False))
        vac_days = max(1, int(constraints.get("vacation_days", 1)))
        group_size = max(1, len(group.get("members", [])))

        centroid = None
        use_meeting_place = False

        if constraints.get("meeting_place"):
            if constraints.get("meeting_place_lat") and constraints.get("meeting_place_lon"):
                centroid = (constraints["meeting_place_lat"], constraints["meeting_place_lon"])
                use_meeting_place = True
                logger.info(f"[Engine] Using meeting place coordinates: {centroid}")
            else:
                geo = await self._geocode(constraints["meeting_place"])
                if geo:
                    centroid = geo
                    use_meeting_place = True
                    logger.info(f"[Engine] Geocoded meeting place '{constraints['meeting_place']}' to {centroid}")

        if not centroid and constraints.get("destination_choice"):
            geo = await self._geocode(constraints["destination_choice"])
            if geo:
                centroid = geo
                logger.info(f"[Engine] Using destination '{constraints['destination_choice']}' at {centroid}")

        if not centroid:
            member_locs = [
                m["location"] for m in group.get("members", [])
                if isinstance(m.get("location"), dict) and m["location"].get("lat")
            ]
            if member_locs:
                centroid = GeoEngine.calculate_centroid(member_locs)
                logger.info(f"[Engine] Using member location centroid: {centroid}")
            else:
                centroid = (16.5062, 80.6480)
                logger.info(f"[Engine] Using default location: {centroid}")

        now = datetime.now(timezone.utc)
        is_weekend = now.weekday() >= 5

        city_name, weather_score = await asyncio.gather(
            self._reverse_geocode(centroid[0], centroid[1]),
            self.weather.score(centroid[0], centroid[1]),
        )

        prefs_cursor = self.db.preferences.find({"group_id": group_id})
        member_prefs = await prefs_cursor.to_list(100)

        group_prefs = self.pref_aggregator.aggregate_preferences(
            [p.get("preferences", {}) for p in member_prefs]
        )

        if budget:
            group_prefs["budget_range"] = budget
        logger.info(f"[Engine] Group prefs: {group_prefs}")

        alpha = float(group_prefs.get("exploration_factor", 1.5))
        self.bandit.set_alpha(alpha)
        logger.info(f"[Engine] RL Alpha set to {alpha}")

        allowed_cats = [c for c in ACTIONS if c in PREF_ALLOWED.get(
            group_prefs.get("indoor_outdoor", "both"), set(ACTIONS)
        )]

        pool = await self._fetch_activities(centroid[0], centroid[1], allowed_cats, group_prefs)

        context = {
            "budget": budget,
            "indoor_outdoor": group_prefs.get("indoor_outdoor", "both"),
            "group_size": group_size,
            "weather_score": weather_score,
            "is_weekend": is_weekend,
        }

        final_schedule: List[Dict] = []
        exclusion_set: set = set()
        days = vac_days if is_vac else 1
        
        for day in range(days):
            day_pool = {cat: list(items) for cat, items in pool.items()}
            daily = self.builder.build(
                day_pool, context, start_min, end_min,
                centroid, group_prefs, exclusion_set
            )
            for item in daily:
                item["day"] = day + 1
            final_schedule.extend(daily)

        summary, reasoning = await self._llm_summary(
            final_schedule, city_name, constraints, group_prefs
        )
        
        return {
            "schedule": final_schedule,
            "reasoning": reasoning,
            "diagnostics": {
                "city": city_name,
                "summary": summary,
                "weather_score": round(weather_score, 2),
                "data_source": "web_search+sample",
                "activity_count": len(final_schedule),
                "budget_tier": budget,
                "indoor_outdoor": pref,
                "group_prefs": group_prefs,
                "centroid": {"lat": centroid[0], "lon": centroid[1]},
            },
        }
    
    async def update_from_feedback(self, recommendation_id: str, feedback: Dict):
        try:
            rec = await self.db.recommendations.find_one({"id": recommendation_id})
            if not rec:
                return
            
            group = await self.db.group_sessions.find_one({"id": rec["group_id"]})
            if not group:
                return
            
            constraints = group.get("constraints", {})
            base_ctx = {
                "budget": constraints.get("budget_range", "medium"),
                "indoor_outdoor": constraints.get("indoor_outdoor", "both"),
                "group_size": max(1, len(group.get("members", []))),
                "weather_score": 0.7,
                "is_weekend": False,
            }
            
            overall = float(feedback.get("overall_satisfaction", 3)) / 5.0 * 2 - 1
            
            for rating in feedback.get("activity_ratings", []):
                cat = rating.get("category", "")
                if cat not in ACTIONS:
                    continue
                
                score = float(rating.get("score", 3))
                reward = (score / 5.0 * 2 - 1) * 0.7 + overall * 0.3
                
                h = 12
                if rating.get("time"):
                    try:
                        h = int(rating["time"].split(":")[0])
                    except Exception:
                        pass
                
                ctx = {
                    **base_ctx,
                    "time_minutes": h * 60,
                    "day_progress": max(0.0, min(1.0, (h - 9) / 12.0)),
                    "diversity_penalty": 0.0,
                }
                
                self.bandit.update(cat, ctx, reward)
                logger.info(f"[RL] Updated arm={cat} reward={reward:.3f}")
            
            await self._save_model()
        except Exception as exc:
            logger.warning(f"Feedback update error: {exc}")

__all__ = [
    "HybridRecommendationEngine",
    "ActivityItem",
    "ActivityAttributes",
    "ContextualThompsonEngine",
    "PreferenceMatcher",
    "GroupPreferenceAggregator",
]