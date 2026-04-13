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
import concurrent.futures

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium_stealth import stealth
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import time

logger = logging.getLogger(__name__)

FEATURE_DIM = 22
ACTIONS = ["dining", "movie", "outdoor_relaxed", "outdoor_active", "cultural", "entertainment"]
TRAVEL_SPEED_KMH = 15.0

MAX_BUDGET_MAP = {"free": 0, "low": 500, "medium": 1500, "high": 5000}

GENRES = ["action", "comedy", "drama", "horror", "romance", "thriller", "sci-fi", 
          "animation", "documentary", "family", "adventure", "mystery", "fantasy"]
CUISINES = ["indian", "chinese", "italian", "mexican", "thai", "japanese", 
            "american", "mediterranean", "korean", "vietnamese", "continental",
            "mughlai", "north_indian", "south_indian", "seafood", "vegetarian", "vegan",
            "biryani", "mandi", "street_food", "bakery", "desserts", "irani"]
ACTIVITY_VIBES = ["relaxing", "adventurous", "romantic", "family_friendly", 
                  "budget_friendly", "luxurious", "social", "cultural", "active",
                  "thrilling", "quirky", "competitive", "playful", "chill"]
TIME_SLOTS = ["morning", "afternoon", "evening", "night", "late_night"]

MEAL_LABEL_MAP = [
    (6.0,  10.5, "Breakfast"),
    (10.5, 12.0, "Brunch"),
    (12.0, 15.0, "Lunch"),
    (15.0, 18.0, "Snacks / Tea Time"),
    (18.0, 21.5, "Dinner"),
    (21.5, 26.0, "Late Night Bites"),
]

def get_meal_label(arrival_h: float) -> str:
    for start, end, label in MEAL_LABEL_MAP:
        if start <= arrival_h < end:
            return label
    return "Meal"

PLACE_TYPE_RULES = {
    "park": {"solo_score": 0.9, "energy": "low", "actions": ["Relaxing walk in", "Enjoy nature at", "Chill out at", "Peaceful time at", "A quiet stroll through"]},
    "cafe": {"solo_score": 0.95, "energy": "low", "actions": ["Coffee break at", "Grab a snack at", "Relaxing time at", "Social caffeine fix at", "Quick refreshment at"]},
    "dining": {"solo_score": 0.7, "energy": "medium", "actions": ["Eat at", "Grab food at", "Enjoy a meal at", "Dine at", "Check out the menu at", "Feed the hunger at"]},
    "mandi": {"solo_score": 0.7, "energy": "medium", "actions": ["Feast on mandi at", "Savour authentic mandi at", "Dig into the biryani at", "Enjoy slow-cooked goodness at"]},
    "biryani": {"solo_score": 0.7, "energy": "medium", "actions": ["Devour biryani at", "Try the legendary biryani at", "Enjoy a bowl of perfection at"]},
    "street_food": {"solo_score": 0.8, "energy": "low", "actions": ["Snack your way through", "Hit the street food at", "Grab some local bites at", "Taste the streets at"]},
    "stadium": {"solo_score": 0.2, "energy": "high", "actions": ["Watch a local match at", "Attend an event at", "Catch some sports at"]},
    "movie": {"solo_score": 0.8, "energy": "low", "actions": ["Watch a movie at", "Catch a film at", "Movie time at", "Enjoy a cinematic experience at"]},
    "museum": {"solo_score": 0.85, "energy": "low", "actions": ["Explore history at", "Admire exhibits at", "Cultural immersion at", "Discover local heritage at"]},
    "entertainment": {"solo_score": 0.6, "energy": "high", "actions": ["Have fun at", "Social hang out at", "Exciting visit to", "Entertainment time at", "Experience the vibe at"]},
    "arcade": {"solo_score": 0.7, "energy": "high", "actions": ["Play games at", "Battle it out at", "Game time at", "Get your game on at", "Challenge each other at"]},
    "bowling": {"solo_score": 0.6, "energy": "medium", "actions": ["Bowl a game at", "Strike it up at", "Hit the lanes at", "Bowl and chill at"]},
    "go-kart": {"solo_score": 0.5, "energy": "high", "actions": ["Race it out at", "Hit the track at", "Floor it at", "Compete on the kart track at"]},
    "escape_room": {"solo_score": 0.3, "energy": "medium", "actions": ["Crack the puzzle at", "Escape from", "Put your minds together at", "Solve the mystery at"]},
    "karaoke": {"solo_score": 0.5, "energy": "medium", "actions": ["Sing your heart out at", "Karaoke night at", "Belt it out at", "Show off your voice at"]},
    "gaming_cafe": {"solo_score": 0.7, "energy": "medium", "actions": ["Game session at", "PC gaming at", "Console battle at", "LAN party vibes at"]},
    "trampoline": {"solo_score": 0.5, "energy": "high", "actions": ["Jump around at", "Bounce off the walls at", "Go airborne at"]},
    "laser_tag": {"solo_score": 0.4, "energy": "high", "actions": ["Laser battle at", "Shoot it out at", "Team deathmatch at"]},
    "outdoor_active": {"solo_score": 0.5, "energy": "high", "actions": ["Get active at", "Play sports at", "Workout at", "Active exploration of", "Energize yourself at"]},
    "default": {"solo_score": 0.5, "energy": "medium", "actions": ["Visit", "Check out", "Explore", "Spend time at"]}
}

SIGNATURE_VIBE_TEMPLATES = {
    "park": [
        "Unwind in the lush greenery of {venue}, where the gentle breeze and peaceful atmosphere make for a perfect escape.",
        "Take a moment to reconnect with nature at {venue}, a serene spot ideal for quiet walks and deep conversations.",
        "Experience the calming vibes of {venue}, where open spaces and local charm provide a much-needed urban retreat."
    ],
    "dining": [
        "Treat your palate to the flavors at {venue}, where authentic {cuisine} and warm hospitality create a memorable meal.",
        "Indulge in a culinary journey at {venue}, a local favorite known for its vibrant {vibe} and delicious offerings.",
        "Savor the unique character of {venue}, where every dish tells a story of local tradition and culinary passion."
    ],
    "mandi": [
        "Gather around the legendary slow-cooked mandi at {venue}, a feast that brings people together with every aromatic bite.",
        "Experience the royal flavors of Yemeni-style mandi at {venue}, where tender meat and fragrant rice create magic.",
        "Let the rich aroma draw you in at {venue}, a beloved mandi house where communal dining is at its finest."
    ],
    "biryani": [
        "Dig into a pot of aromatic biryani at {venue}, where spice, saffron, and slow-cooking come together in every mouthful.",
        "Treat yourself to the city's finest biryani at {venue}, a local institution loved by all serious rice lovers.",
        "Unbox the layers of flavour at {venue}, where biryani is not just food — it's an experience."
    ],
    "street_food": [
        "Hit the buzzing street food scene at {venue}, where quick bites and bold flavours define the local food culture.",
        "Graze your way through {venue}, sampling the city's most authentic street snacks in one vibrant spot."
    ],
    "movie": [
        "Immerse yourselves in a cinematic escape at {venue}, where the latest stories come to life in a premium setting.",
        "Enjoy the magic of the big screen at {venue}, a perfect spot for movie lovers to relax and be entertained.",
        "Switch off and dive into a world of film at {venue}, featuring top-tier comfort and a truly engaging atmosphere."
    ],
    "museum": [
        "Step into the fascinating world of history at {venue}, where every exhibit offers a window into our rich heritage.",
        "Explore the artistic and cultural soul of the region at {venue}, a place where the past meets the present.",
        "Ignite your curiosity at {venue}, where captivating displays and local stories wait to be discovered."
    ],
    "outdoor_active": [
        "Get your heart pumping at {venue}, an energetic destination perfect for sports, movement, and group fun.",
        "Release your energy at {venue}, where the vibrant atmosphere and active vibe keep the excitement going.",
        "Push your limits and enjoy the outdoors at {venue}, the ideal spot for an action-packed interval in your day."
    ],
    "entertainment": [
        "Experience the high-energy vibe of {venue}, a top-rated spot for entertainment and social engagement.",
        "Dive into the fun at {venue}, where the lively atmosphere and unique attractions guarantee a great time.",
        "Make some memories at {venue}, a place where excitement and group connection come together naturally."
    ],
    "arcade": [
        "Level up your day at {venue}, where rows of arcade machines and competitive energy keep things exciting.",
        "Battle each other across dozens of games at {venue}, the go-to spot for serious fun and friendly rivalry.",
        "Step into {venue} and embrace your inner gamer — it's all about high scores and big laughs here."
    ],
    "bowling": [
        "Hit the lanes at {venue} for a few frames of friendly competition and good vibes.",
        "Bowling at {venue} is the perfect mix of chill and competitive — everyone walks away smiling.",
        "Roll, spare, and strike your way through a fun-filled session at {venue}."
    ],
    "go-kart": [
        "Buckle up and race each other around the track at {venue} — speed, adrenaline, and bragging rights await.",
        "Feel the rush at {venue}'s go-kart track, where friendly competition fuels the best memories.",
        "Who's the fastest in the group? Find out at {venue} — the ultimate go-kart showdown."
    ],
    "escape_room": [
        "Put your problem-solving skills to the test at {venue}, where teamwork is the only way out.",
        "Unlock clues, crack codes, and escape together from {venue}'s immersive puzzle room experience.",
        "{venue} tests your group's creativity and communication in the most thrilling way possible."
    ],
    "karaoke": [
        "Grab the mic and steal the show at {venue} — no talent required, just confidence and good vibes.",
        "Belt out your favourite tracks at {venue}, where the stage is yours and every song is a hit.",
        "Karaoke at {venue} turns a normal evening into an unforgettable memory — sing, laugh, repeat."
    ],
    "gaming_cafe": [
        "Boot up, log in, and battle it out at {venue}, where gaming setups and high-speed connections await.",
        "Whether it's PC, console, or board games, {venue} has everything for an epic gaming session."
    ],
    "trampoline": [
        "Bounce, flip, and soar at {venue} — the trampoline park that turns adults back into kids.",
        "Jump your way to a great mood at {venue}, where every leap comes with a burst of pure fun."
    ],
    "laser_tag": [
        "Gear up and light up the arena at {venue} in an adrenaline-charged laser tag battle.",
        "Team up or go solo at {venue}'s laser tag zone — strategy, stealth, and a whole lot of fun."
    ],
    "default": [
        "Discover the unique atmosphere of {venue}, a local gem that reflects the true character of the city.",
        "Enjoy a tailored experience at {venue}, chosen specifically to match your group's preferred energy and style.",
        "Make the most of your visit to {venue}, a standout destination that always delivers a great vibe."
    ]
}

@dataclass
class ActivityAttributes:
    genres: List[str] = field(default_factory=list)
    cuisines: List[str] = field(default_factory=list)
    vibes: List[str] = field(default_factory=list)
    time_slots: List[str] = field(default_factory=list)
    suitable_for_groups: bool = True
    age_restriction: str = "all"
    booking_required: bool = False
    popularity_score: float = 0.5
    rating: float = 3.5
    action_title: str = ""
    energy_profile: str = "medium"
    solo_score: float = 0.5
    exact_start_times: List[int] = field(default_factory=list)
    
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
class ProxyManager:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]
        self.proxies = [
            None,
        ]
        self._proxy_index = 0

    def get_random_ua(self) -> str:
        return random.choice(self.user_agents)

    def get_next_proxy(self) -> Optional[str]:
        if not self.proxies: return None
        p = self.proxies[self._proxy_index]
        self._proxy_index = (self._proxy_index + 1) % len(self.proxies)
        return p

class BrowserManager:
    def __init__(self):
        self.proxy_mgr = ProxyManager()
        self._service = None

    def _init_service(self):
        if not self._service:
            self._service = Service(ChromeDriverManager().install())
        return self._service

    def get_stealth_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        ua = self.proxy_mgr.get_random_ua()
        options.add_argument(f"user-agent={ua}")
        
        proxy = self.proxy_mgr.get_next_proxy()
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')

        driver = webdriver.Chrome(service=self._init_service(), options=options)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        if SELENIUM_AVAILABLE:
            try:
                stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                )
            except Exception as e:
                logger.warning(f"Stealth application failed: {e}")
        
        return driver

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
            "rating": self.attributes.rating,
            "popularity_score": self.attributes.popularity_score,
            "action_title": self.attributes.action_title,
            "energy_profile": self.attributes.energy_profile,
            "solo_score": self.attributes.solo_score,
            "exact_start_times": self.attributes.exact_start_times,
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
            rating=data.get("rating", 3.5),
            popularity_score=data.get("popularity_score", 0.5),
            action_title=data.get("action_title", ""),
            energy_profile=data.get("energy_profile", "medium"),
            solo_score=data.get("solo_score", 0.5),
            exact_start_times=data.get("exact_start_times", [])
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

class GoogleMapsScraper:
    def __init__(self, browser_mgr: BrowserManager):
        self.browser_mgr = browser_mgr

    def scrape_nearby(self, category: str, lat: float, lon: float, query_prefix: str = "") -> List[Dict]:
        if not SELENIUM_AVAILABLE: return []

        search_query = f"{query_prefix} {category}".strip()
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/@{lat},{lon},15z"
        
        driver = self.browser_mgr.get_stealth_driver()
        results = []
        try:
            logger.info(f"[Selenium] Maps Stealth Nav: {url}")
            driver.get(url)
            
            time.sleep(random.uniform(2, 4))
            
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed'], .hfpxzc")))
            except Exception:
                logger.warning("[Selenium] Maps Container Timeout")
                return []

            elements = driver.find_elements(By.CSS_SELECTOR, "div[role='article'], .hfpxzc")
            for el in elements[:10]:
                try:
                    if random.random() > 0.7: time.sleep(random.uniform(0.1, 0.4))
                    
                    name = el.get_attribute("aria-label") or "Unknown"
                    if not name or name == "Unknown":
                        try: name = el.find_element(By.CSS_SELECTOR, ".qBF1Pd").text
                        except: pass

                    rating = 4.0
                    try:
                        rating_text = el.find_element(By.CSS_SELECTOR, ".MW4etd").text
                        if rating_text: rating = float(rating_text)
                    except: pass

                    results.append({
                        "name": name,
                        "rating": rating,
                        "lat": lat + random.uniform(-0.005, 0.005),
                        "lon": lon + random.uniform(-0.005, 0.005),
                        "source": "google_maps_scrape"
                    })
                except: continue
        except Exception as e:
            logger.error(f"[Selenium] Maps Scrape Failure: {e}")
        finally:
            driver.quit()
        return results

class BookMyShowScraper:
    def __init__(self, browser_mgr: BrowserManager):
        self.browser_mgr = browser_mgr

    def _parse_bms_time(self, time_str: str) -> int:
        time_str = time_str.strip().upper()
        try:
            if "AM" in time_str or "PM" in time_str:
                t = datetime.strptime(time_str, "%I:%M %p")
            else:
                t = datetime.strptime(time_str, "%H:%M")
            return t.hour * 60 + t.minute
        except:
            return None

    def _scrape_theatres_and_timings(self, driver, movie_url: str) -> List[Dict]:
        venues = []
        try:
            logger.info(f"[Selenium] Navigating to movie page: {movie_url}")
            driver.get(movie_url)
            time.sleep(3)
            
            buttons = driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book tickets')]")
            if buttons:
                driver.execute_script("arguments[0].click();", buttons[0])
                time.sleep(4)
                
                format_pills = driver.find_elements(By.XPATH, "//span[contains(text(), '2D')]")
                if format_pills:
                    try:
                        driver.execute_script("arguments[0].click();", format_pills[0])
                        time.sleep(3)
                    except: pass

                elements = driver.find_elements(By.CSS_SELECTOR, "ul#venuelist li")
                for el in elements[:3]:
                    v_name_tag = el.find_elements(By.CSS_SELECTOR, ".venue-info-text, .__venue-name")
                    v_name = v_name_tag[0].text.strip() if v_name_tag else "Local Cinema"
                        
                    showtime_pills = el.find_elements(By.CSS_SELECTOR, "a.showtime-pill, div.showtime-pill")
                    timings = []
                    cost = 150
                    for pill in showtime_pills[:5]:
                        t_text = pill.text.strip()
                        if ":" in t_text:
                            price_str = pill.get_attribute("data-price")
                            if price_str and price_str.isdigit(): cost = int(price_str)
                            t_min = self._parse_bms_time(t_text)
                            if t_min is not None: timings.append(t_min)
                    if timings:
                        venues.append({"name": v_name, "cost": cost, "timings": timings})
        except Exception as e:
            logger.warning(f"[Scraper] BMS Deep scrape failed: {e}")
        return venues

    def scrape_movies(self, city: str) -> List[Dict]:
        if not SELENIUM_AVAILABLE: return []
        
        clean_city = city.lower().replace(" ", "-")
        url = f"https://in.bookmyshow.com/explore/movies-{clean_city}"
        
        driver = self.browser_mgr.get_stealth_driver()
        movies = []
        try:
            logger.info(f"[Selenium] BMS Stealth Nav: {url}")
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/movies/']")
            movie_cards = []
            
            for el in elements[:5]:
                try:
                    href = el.get_attribute("href")
                    if not href: continue
                    text = el.text.split("\n")
                    if len(text) < 1: continue
                    
                    title = text[0]
                    rating = 4.0
                    genre = "Drama"
                    
                    for line in text:
                        if "/10" in line:
                            try: rating = float(line.split("/")[0])
                            except: pass
                        if any(g in line for g in ["Action", "Comedy", "Thriller", "Horror", "Drama", "Sci-Fi", "Animation"]):
                            genre = line
                    
                    movie_cards.append({
                        "name": title,
                        "rating": rating,
                        "genre": genre,
                        "url": href
                    })
                except: continue

            for card in movie_cards[:3]:
                card["theatres"] = self._scrape_theatres_and_timings(driver, card["url"])
                movies.append(card)
                time.sleep(3)
                
        except Exception as e:
            logger.error(f"[Selenium] BMS Scrape Failure: {e}")
        finally:
            try: driver.quit()
            except: pass
            
        return movies

class WebDataFetcher:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(3)
        self._cache: Dict[str, Tuple[List[Dict], float]] = {}
        self._cache_duration = 3600
        self._cli_available = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._browser_mgr = BrowserManager()
        self._maps_scraper = GoogleMapsScraper(self._browser_mgr)
        self._bms_scraper = BookMyShowScraper(self._browser_mgr)

    def _enrich_item(self, item: ActivityItem, place_type: str) -> ActivityItem:
        rules = PLACE_TYPE_RULES.get(place_type, PLACE_TYPE_RULES["default"])
        item.attributes.energy_profile = rules["energy"]
        item.attributes.solo_score = rules["solo_score"]
        action = random.choice(rules["actions"])
        item.attributes.action_title = f"{action} {item.name}"
        return item

    async def _search_selenium_fallback(self, category: str, lat: float, lon: float, query_prefix: str = "") -> List[ActivityItem]:
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                self._executor, 
                self._maps_scraper.scrape_nearby,
                category, lat, lon, query_prefix
            )
            
            items = []
            engine_cat = category
            if category == "cinema": engine_cat = "movie"
            elif category == "restaurant": engine_cat = "dining"
            elif "outdoor relaxed" in category: engine_cat = "outdoor_relaxed"
            elif "outdoor active" in category: engine_cat = "outdoor_active"
            elif category == "attractions": engine_cat = "entertainment"

            for r in results:
                new_item = ActivityItem(
                    name=r["name"],
                    category=engine_cat,
                    cost=random.randint(200, 1000),
                    duration=120,
                    lat=r["lat"],
                    lon=r["lon"],
                    attributes=ActivityAttributes(
                        vibes=["social", "popular"],
                        rating=r["rating"],
                        popularity_score=0.8
                    ),
                    source="google_maps_scrape"
                )
                self._enrich_item(new_item, engine_cat)
                items.append(new_item)
            return items
        except Exception as e:
            logger.error(f"Selenium fallback failed: {e}")
            return []
    
    def _is_generic_name(self, name: str) -> bool:
        if not name: return True
        generics = [
            "park", "garden", "way", "node", "hotel", "restaurant", "cafe", 
            "stadium", "museum", "caves", "entrance", "playground", "temple",
            "mosque", "church", "toilet", "parking", "bus stop", "atm", "hospital",
            "medical", "school", "college", "university", "bank", "shop", "office"
        ]
        n = name.lower().strip()
        if n in generics or len(n) < 3: return True
        if n.startswith("the ") and n[4:] in generics: return True
        if n.startswith("local ") and n[6:] in generics: return True
        if n.replace(".", "").replace(" ", "").isdigit(): return True
        return False

    async def _overpass_query(self, query: str) -> List[Dict]:
        mirrors = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.osm.ch/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://z.overpass-api.de/api/interpreter",
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
    
    async def search_movies(self, lat: float, lon: float, city: str = "Mumbai", genres: List[str] = None) -> List[ActivityItem]:
        cache_key = f"movies_real_{lat}_{lon}_{city}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if datetime.now().timestamp() - ts < self._cache_duration:
                return [ActivityItem.from_dict(d) for d in data]
        
        logger.info(f"[Fetch] Attempting localized BookMyShow search for {city}...")
        results = await asyncio.get_event_loop().run_in_executor(
            self._executor, self._bms_scraper.scrape_movies, city
        )
        
        items = []
        
        for r in results:
            if r.get("theatres"):
                for t in r["theatres"]:
                    if not t["timings"]: continue
                    items.append(ActivityItem(
                        name=f"{t['name']}: {r['name']}",
                        category="movie",
                        cost=t["cost"],
                        duration=150,
                        lat=lat,
                        lon=lon,
                        attributes=ActivityAttributes(
                            genres=[r['genre']],
                            rating=r['rating'],
                            popularity_score=0.9,
                            exact_start_times=t["timings"]
                        ),
                        source="live_bms_deep_scrape"
                    ))
        
        if items:
            logger.info(f"[Fetch] Successfully pulled {len(items)} real-time movie slots from BMS deep scrape.")
            self._cache[cache_key] = ([i.to_dict() for i in items], datetime.now().timestamp())
            return items

        query = f"""[out:json][timeout:25];
        (node["amenity"="cinema"](around:10000,{lat},{lon});
         way["amenity"="cinema"](around:10000,{lat},{lon}););
        out center;"""
        elements = await self._overpass_query(query)
        
        if not elements:
            logger.info("[Fetch] Overpass failed for cinemas. Using Maps fallback...")
            cinema_locs = await self._search_selenium_fallback("cinema", lat, lon, "cinemas near")
            elements = [{"lat": c.lat, "lon": c.lon, "tags": {"name": c.name}} for c in cinema_locs]

        movie_pool = results[:3] if results else [
            {"name": "Current Blockbuster", "genre": "Action", "rating": 4.5},
            {"name": "Romantic Escape", "genre": "Romance", "rating": 4.2},
            {"name": "Midnight Thrills", "genre": "Thriller", "rating": 4.0}
        ]

        for el in elements:
            base_name = el.get("tags", {}).get("name", "Local Cinema")
            c_lat = el.get("lat") or el.get("center", {}).get("lat", lat)
            c_lon = el.get("lon") or el.get("center", {}).get("lon", lon)
            for r in movie_pool:
                items.append(ActivityItem(
                    name=f"{base_name}: {r['name']}",
                    category="movie",
                    cost=150,
                    duration=150,
                    lat=c_lat,
                    lon=c_lon,
                    attributes=ActivityAttributes(
                        genres=[r['genre']],
                        rating=r['rating'],
                        popularity_score=0.9
                    ),
                    source="live_cinema_node"
                ))

        if not items:
            logger.warning("[Fetch] Movie search completely failed. Using internal samples.")
            return self._get_sample_movies("Current", genres)
            
        self._cache[cache_key] = ([i.to_dict() for i in items], datetime.now().timestamp())
        return items

    async def _search_web_internal(self, query: str, preferred_genres: List[str] = None) -> List[Dict]:
        movie_database = {
            "action": ["Vanguard Protocol", "Shadow Operative", "Steel Torrent", "Urban Warfare: Zero Hour", "The Last Mercenary"],
            "comedy": ["Laugh Out Loud", "The Misadventures of Mike", "Gigglestorm", "Family Feud: The Movie", "Office Chaos"],
            "drama": ["Echoes of Silence", "The Long Road Home", "Fractured Reality", "Beyond the Horizon", "Legacy of the Brave"],
            "horror": ["Nightshade", "The Whispering Woods", "Crimson Peak", "Descent into Darkness", "The Unseen"],
            "sci-fi": ["Nebula Horizon", "Quantum Leap", "Cyberpunk Revolt", "The Andromeda Strain", "Stellar Voyage"],
            "thriller": ["Deadly Pursuit", "The Silent Witness", "Infiltration", "Cold Trail", "Point of No Return"],
            "romance": ["Love in Bloom", "Autumn Whispers", "Eternal Flame", "Heartbeat City", "The Secret Letter"],
            "animation": ["Cloudy with a Chance of Magic", "The Whimsical Woods", "Intergalactic Pets", "Little Heroes", "Skyward Journey"],
        }
        
        results = []
        target_genres = preferred_genres if preferred_genres else list(movie_database.keys())
        
        for g in target_genres:
            if g in movie_database:
                for m in movie_database[g]:
                    results.append({"name": m, "snippet": f"A thrilling {g} movie showing now.", "genre": g})
        
        random.shuffle(results)
        return results[:15]

    def _extract_movie_list_from_search(self, results: List, genres: List[str] = None) -> List[str]:
        return [r["name"] for r in results]
    
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
          node["amenity"~"restaurant|cafe|fast_food|pizzeria"](around:4000,{lat},{lon});
          way["amenity"~"restaurant|cafe|fast_food|pizzeria"](around:4000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name or self._is_generic_name(name):
                continue
            cuisine_tag = tags.get("cuisine", "").lower().split(";")
            found_cuisines = [c.strip() for c in cuisine_tag if c.strip() in CUISINES] or ["indian"]
            cost = self._get_realistic_cost("dining", tags.get("cuisine", ""), budget)
            new_item = ActivityItem(
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
                    rating=random.uniform(4.0, 4.8)
                ),
                source="overpass"
            )
            self._enrich_item(new_item, "dining")
            items.append(new_item)
        if not items:
            logger.info("[Fetch] Overpass returned no restaurants. Triggering Selenium fallback...")
            items = await self._search_selenium_fallback("restaurant", lat, lon, " ".join(cuisines or []))
            if not items:
                items = self._get_sample_restaurants("Current", cuisines, budget)
        self._cache[cache_key] = ([i.to_dict() for i in items], datetime.now().timestamp())
        return items
    
    async def search_events(self, lat: float, lon: float, event_type: str = "all") -> List[ActivityItem]:
        query = f"""
        [out:json][timeout:30];
        (
          node["tourism"~"attraction|museum|gallery|zoo|theme_park"](around:4000,{lat},{lon});
          way["tourism"~"attraction|museum|gallery|zoo|theme_park"](around:4000,{lat},{lon});
          node["leisure"~"amusement_arcade|bowling_alley|karting|laser_game|escape_game|trampoline_park|miniature_golf|water_park"](around:4000,{lat},{lon});
          way["leisure"~"amusement_arcade|bowling_alley|karting|laser_game|escape_game|trampoline_park|miniature_golf|water_park"](around:4000,{lat},{lon});
          node["amenity"~"nightclub|casino|theatre"](around:4000,{lat},{lon});
          way["amenity"~"nightclub|casino|theatre"](around:4000,{lat},{lon});
          node["sport"~"climbing|skating|swimming|tennis|badminton|squash|billiards|table_tennis"](around:4000,{lat},{lon});
          way["sport"~"climbing|skating|swimming|tennis|badminton|squash|billiards|table_tennis"](around:4000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        blacklist = ["aadhar", "seva", "kendram", "office", "bank", "department",
                     "municipality", "development", "service", "center", "corporation", "stadium"]

        FUN_VENUE_MAP = {
            "amusement_arcade": ("arcade", "entertainment", ["social", "playful", "competitive"], 75),
            "bowling_alley":    ("bowling", "entertainment", ["social", "competitive", "family_friendly"], 90),
            "karting":          ("go-kart", "entertainment", ["thrilling", "competitive", "social"], 60),
            "laser_game":       ("laser_tag", "entertainment", ["thrilling", "competitive", "social"], 50),
            "escape_game":      ("escape_room", "entertainment", ["adventurous", "social", "competitive"], 70),
            "trampoline_park":  ("trampoline", "entertainment", ["active", "thrilling", "playful"], 60),
            "miniature_golf":   ("entertainment", "entertainment", ["social", "playful", "family_friendly"], 60),
            "water_park":       ("outdoor_active", "entertainment", ["thrilling", "active", "social"], 180),
        }

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name or self._is_generic_name(name):
                continue
            if any(term in name.lower() for term in blacklist):
                continue

            leisure_val = tags.get("leisure", "")
            amenity_val = tags.get("amenity", "")
            tourism_val = tags.get("tourism", "")

            if leisure_val in FUN_VENUE_MAP:
                place_type, category, vibes, duration = FUN_VENUE_MAP[leisure_val]
            elif amenity_val in ("nightclub", "casino"):
                place_type, category, vibes, duration = "entertainment", "entertainment", ["social", "adventurous"], 120
            elif tourism_val == "museum" or "museum" in name.lower():
                place_type, category, vibes, duration = "museum", "cultural", ["cultural", "social"], 90
            elif tags.get("sport"):
                place_type, category, vibes, duration = "outdoor_active", "entertainment", ["active", "social", "competitive"], 90
            else:
                place_type, category, vibes, duration = "entertainment", "entertainment", ["social", "entertaining"], 120

            new_item = ActivityItem(
                name=name,
                category=category,
                cost=random.randint(100, 700),
                duration=duration,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    vibes=vibes,
                    time_slots=["afternoon", "evening", "night"],
                    rating=random.uniform(4.0, 4.8),
                    popularity_score=random.uniform(0.75, 0.95)
                ),
                source="overpass"
            )
            self._enrich_item(new_item, place_type)
            items.append(new_item)
        if not items:
            logger.info(f"[Fetch] Overpass returned no {event_type} events. Triggering Selenium fallback...")
            items = await self._search_selenium_fallback(event_type if event_type != "all" else "attractions", lat, lon)
            if not items:
                items = self._get_sample_events("Current", event_type)
        return items
    
    async def search_outdoor_activities(self, lat: float, lon: float, activity_type: str,
                                        vibe: str = None) -> List[ActivityItem]:
        query = f"""
        [out:json][timeout:25];
        (
          node["leisure"~"park|garden|nature_reserve|playground"](around:4000,{lat},{lon});
          way["leisure"~"park|garden|nature_reserve|playground"](around:4000,{lat},{lon});
        );
        out center;
        """
        elements = await self._overpass_query(query)
        items = []
        blacklist = ["aadhar", "seva", "kendram", "office", "bank", "department", 
                     "municipality", "development", "service", "center", "corporation"]
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name or self._is_generic_name(name):
                continue
            if any(term in name.lower() for term in blacklist):
                continue
            
            p_type = "park" if "park" in tags.values() else "outdoor_active"
            
            new_item = ActivityItem(
                name=name,
                category="outdoor_relaxed",
                cost=0,
                duration=90,
                lat=el.get("lat") or el.get("center", {}).get("lat", lat),
                lon=el.get("lon") or el.get("center", {}).get("lon", lon),
                attributes=ActivityAttributes(
                    vibes=["relaxing", "family_friendly"],
                    time_slots=["morning", "afternoon", "evening"],
                    rating=4.5
                ),
                source="overpass"
            )
            self._enrich_item(new_item, p_type)
            items.append(new_item)
        if not items:
            query_str = "parks nearby" if "relaxed" in activity_type else "activities nearby"
            items = await self._search_selenium_fallback(activity_type.replace("_", " "), lat, lon, query_prefix=query_str)
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
        movie_pool = [
            ("Cinema: Galactic Odyssey", ["sci-fi", "action", "adventure"], 450),
            ("Cinema: Whispers of the Heart", ["romance", "drama"], 420),
            ("Cinema: The Parallel Universe", ["sci-fi", "thriller", "mystery"], 480),
            ("Cinema: Midnight Masquerade", ["mystery", "thriller"], 440),
            ("Cinema: Neon City Nights", ["action", "thriller"], 460),
            ("Cinema: The Last Waltz", ["drama", "romance"], 400),
            ("Cinema: Cosmic Convergence", ["sci-fi", "mystery"], 470),
            ("Cinema: Laughter Unlimited", ["comedy"], 380),
            ("Cinema: The Silent Echo", ["drama", "mystery"], 410),
            ("Cinema: Skyward Bound", ["animation", "adventure", "family"], 350),
        ]
        
        sample_movies = []
        for name, m_genres, cost in movie_pool:
            sample_movies.append(ActivityItem(
                name=name,
                category="movie",
                cost=cost,
                duration=145,
                attributes=ActivityAttributes(
                    genres=m_genres,
                    vibes=["social", "entertaining"],
                    time_slots=["afternoon", "evening", "night"],
                    suitable_for_groups=True,
                    booking_required=True,
                    popularity_score=0.82,
                    rating=4.3
                ),
                source="sample"
            ))
            
        if genres:
            filtered = [m for m in sample_movies if any(g in m.attributes.genres for g in genres)]
            if filtered:
                sample_movies = filtered
                
        for m in sample_movies:
            m.lat = 0.005 * random.uniform(-1, 1)
            m.lon = 0.005 * random.uniform(-1, 1)
            
        return sample_movies
    
    def _get_sample_restaurants(self, location: str, cuisines: List[str] = None,
                                 budget: str = "medium") -> List[ActivityItem]:
        max_cost = MAX_BUDGET_MAP.get(budget, 60)
        sample_restaurants = [
            ActivityItem(name="The Royal Indian Kitchen", category="dining", cost=18, duration=65,
                attributes=ActivityAttributes(cuisines=["indian", "north_indian"], vibes=["social", "luxurious"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.3)),
            ActivityItem(name="Dragon Palace Chinese", category="dining", cost=16, duration=55,
                attributes=ActivityAttributes(cuisines=["chinese"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.75, rating=4.1)),
            ActivityItem(name="Pasta Paradise Italian", category="dining", cost=20, duration=60,
                attributes=ActivityAttributes(cuisines=["italian"], vibes=["romantic", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.78, rating=4.2)),
            ActivityItem(name="Taco Fiesta Mexican", category="dining", cost=14, duration=50,
                attributes=ActivityAttributes(cuisines=["mexican"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.70, rating=4.0)),
            ActivityItem(name="Thai Orchid Garden", category="dining", cost=17, duration=55,
                attributes=ActivityAttributes(cuisines=["thai"], vibes=["social", "cultural"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.72, rating=4.1)),
            ActivityItem(name="Sushi Master Japanese", category="dining", cost=25, duration=60,
                attributes=ActivityAttributes(cuisines=["japanese"], vibes=["luxurious", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Dosa Plaza South Indian", category="dining", cost=8, duration=40,
                attributes=ActivityAttributes(cuisines=["south_indian", "vegetarian"], vibes=["budget_friendly", "family_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.2)),
            ActivityItem(name="BBQ Nation Grill House", category="dining", cost=22, duration=90,
                attributes=ActivityAttributes(cuisines=["american", "indian"], vibes=["social", "family_friendly"],
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    popularity_score=0.88, rating=4.4)),
            ActivityItem(name="Green Bowl Vegan Cafe", category="dining", cost=15, duration=45,
                attributes=ActivityAttributes(cuisines=["vegan", "vegetarian", "mediterranean"], vibes=["budget_friendly", "social"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.65, rating=4.3)),
            ActivityItem(name="Chai & Snacks Corner", category="dining", cost=4, duration=30,
                attributes=ActivityAttributes(cuisines=["indian"], vibes=["budget_friendly", "social"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.75, rating=4.0)),
            ActivityItem(name="Fine Dining at The Grand", category="dining", cost=50, duration=90,
                attributes=ActivityAttributes(cuisines=["continental", "mediterranean"], vibes=["luxurious", "romantic"],
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    popularity_score=0.92, rating=4.7)),
            ActivityItem(name="Korean BBQ House", category="dining", cost=20, duration=75,
                attributes=ActivityAttributes(cuisines=["korean"], vibes=["social", "family_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.78, rating=4.3)),
            ActivityItem(name="Free Community Kitchen", category="dining", cost=0, duration=40,
                attributes=ActivityAttributes(cuisines=["indian", "vegetarian"], vibes=["budget_friendly", "cultural"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.60, rating=4.0)),
            ActivityItem(name="Street Food Junction", category="dining", cost=5, duration=35,
                attributes=ActivityAttributes(cuisines=["indian", "street_food"], vibes=["budget_friendly", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.1)),
            ActivityItem(name="Seafood Paradise", category="dining", cost=22, duration=60,
                attributes=ActivityAttributes(cuisines=["seafood", "indian"], vibes=["social", "luxurious"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.4)),
            ActivityItem(name="Al-Kabsa Mandi House", category="dining", cost=18, duration=75,
                attributes=ActivityAttributes(cuisines=["mandi", "mughlai"], vibes=["social", "cultural", "luxurious"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.91, rating=4.7)),
            ActivityItem(name="Biryani Darbar", category="dining", cost=14, duration=55,
                attributes=ActivityAttributes(cuisines=["biryani", "north_indian", "mughlai"], vibes=["social", "budget_friendly"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.93, rating=4.6)),
            ActivityItem(name="Hyderabadi Biryani House", category="dining", cost=12, duration=50,
                attributes=ActivityAttributes(cuisines=["biryani", "south_indian"], vibes=["budget_friendly", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.89, rating=4.5)),
            ActivityItem(name="Haleem & More", category="dining", cost=8, duration=40,
                attributes=ActivityAttributes(cuisines=["mughlai", "north_indian"], vibes=["budget_friendly", "cultural"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.3)),
            ActivityItem(name="Chettinad Spice Garden", category="dining", cost=16, duration=60,
                attributes=ActivityAttributes(cuisines=["south_indian", "indian"], vibes=["cultural", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.77, rating=4.4)),
            ActivityItem(name="Pav Bhaji Street Corner", category="dining", cost=3, duration=25,
                attributes=ActivityAttributes(cuisines=["street_food", "indian"], vibes=["budget_friendly", "social", "playful"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.85, rating=4.2)),
            ActivityItem(name="Irani Café & Bun Maska", category="dining", cost=4, duration=30,
                attributes=ActivityAttributes(cuisines=["irani", "bakery"], vibes=["chill", "cultural", "budget_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.5)),
            ActivityItem(name="Filter Coffee & Idli House", category="dining", cost=4, duration=30,
                attributes=ActivityAttributes(cuisines=["south_indian", "indian"], vibes=["budget_friendly", "chill"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.88, rating=4.3)),
            ActivityItem(name="Waffles & Crepes Café", category="dining", cost=9, duration=40,
                attributes=ActivityAttributes(cuisines=["desserts", "bakery"], vibes=["social", "romantic", "playful"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.78, rating=4.4)),
            ActivityItem(name="Mughlai Darbar", category="dining", cost=20, duration=70,
                attributes=ActivityAttributes(cuisines=["mughlai", "north_indian"], vibes=["luxurious", "cultural"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.83, rating=4.5)),
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
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Comedy Night - Stand Up Special", category="entertainment", cost=18, duration=90,
                attributes=ActivityAttributes(genres=["comedy"], vibes=["entertaining", "social"],
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.80, rating=4.3)),
            ActivityItem(name="Art Gallery Exhibition Opening", category="cultural", cost=10, duration=90,
                attributes=ActivityAttributes(vibes=["cultural", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.65, rating=4.2)),
            ActivityItem(name="Escape Room — The Lost Temple", category="entertainment", cost=24, duration=70,
                attributes=ActivityAttributes(vibes=["adventurous", "social", "competitive"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.91, rating=4.7)),
            ActivityItem(name="Bowling at Strike Zone", category="entertainment", cost=16, duration=90,
                attributes=ActivityAttributes(vibes=["social", "family_friendly", "competitive"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.1)),
            ActivityItem(name="Jazz Lounge Evening", category="entertainment", cost=20, duration=120,
                attributes=ActivityAttributes(genres=["music"], vibes=["relaxing", "romantic"],
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.75, rating=4.4)),
            ActivityItem(name="Free Outdoor Concert", category="entertainment", cost=0, duration=150,
                attributes=ActivityAttributes(genres=["music"], vibes=["social", "budget_friendly"],
                    time_slots=["evening"], suitable_for_groups=True,
                    popularity_score=0.90, rating=4.3)),
            ActivityItem(name="Theatre Play - The Last Act", category="cultural", cost=25, duration=150,
                attributes=ActivityAttributes(genres=["drama"], vibes=["cultural", "social"],
                    time_slots=["evening"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.70, rating=4.5)),
            ActivityItem(name="Karaoke Night — Sing Your Heart Out", category="entertainment", cost=12, duration=120,
                attributes=ActivityAttributes(vibes=["social", "playful", "entertaining"],
                    time_slots=["evening", "night"], suitable_for_groups=True,
                    popularity_score=0.83, rating=4.2)),
            ActivityItem(name="Museum Special Exhibition", category="cultural", cost=12, duration=120,
                attributes=ActivityAttributes(vibes=["cultural", "social"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.68, rating=4.4)),
            ActivityItem(name="Timezone Arcade & Gaming Zone", category="entertainment", cost=18, duration=90,
                attributes=ActivityAttributes(vibes=["social", "playful", "competitive", "thrilling"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.90, rating=4.5)),
            ActivityItem(name="VR World — Virtual Reality Hub", category="entertainment", cost=22, duration=60,
                attributes=ActivityAttributes(vibes=["thrilling", "social", "adventurous"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.88, rating=4.6)),
            ActivityItem(name="Go-Kart Racing Track", category="entertainment", cost=20, duration=60,
                attributes=ActivityAttributes(vibes=["thrilling", "competitive", "adventurous", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.92, rating=4.7)),
            ActivityItem(name="Laser Tag Arena — Neon Zone", category="entertainment", cost=15, duration=45,
                attributes=ActivityAttributes(vibes=["thrilling", "competitive", "social"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    booking_required=True, popularity_score=0.87, rating=4.5)),
            ActivityItem(name="Trampoline Park — Sky Jump", category="entertainment", cost=18, duration=60,
                attributes=ActivityAttributes(vibes=["active", "thrilling", "playful", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.85, rating=4.4)),
            ActivityItem(name="Billiards & Snooker Club", category="entertainment", cost=10, duration=90,
                attributes=ActivityAttributes(vibes=["chill", "social", "competitive"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.76, rating=4.1)),
            ActivityItem(name="Gaming Café — LAN Party Zone", category="entertainment", cost=12, duration=120,
                attributes=ActivityAttributes(vibes=["social", "playful", "competitive"],
                    time_slots=["afternoon", "evening", "night"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.2)),
            ActivityItem(name="Indoor Rock Climbing Wall", category="entertainment", cost=20, duration=90,
                attributes=ActivityAttributes(vibes=["adventurous", "active", "thrilling"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.5)),
            ActivityItem(name="Badminton & Sports Complex", category="entertainment", cost=8, duration=60,
                attributes=ActivityAttributes(vibes=["active", "social", "competitive"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.78, rating=4.0)),
            ActivityItem(name="Mini Golf Adventure Park", category="entertainment", cost=14, duration=75,
                attributes=ActivityAttributes(vibes=["social", "family_friendly", "playful"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.81, rating=4.3)),
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
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.85, rating=4.5)),
            ActivityItem(name="Botanical Garden Visit", category="outdoor_relaxed", cost=5, duration=90,
                attributes=ActivityAttributes(vibes=["relaxing", "cultural"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.75, rating=4.3)),
            ActivityItem(name="Sunset Beach Walk", category="outdoor_relaxed", cost=0, duration=60,
                attributes=ActivityAttributes(vibes=["relaxing", "romantic"],
                    time_slots=["evening"], suitable_for_groups=True,
                    popularity_score=0.90, rating=4.7)),
            ActivityItem(name="Lake Viewpoint Picnic", category="outdoor_relaxed", cost=0, duration=120,
                attributes=ActivityAttributes(vibes=["relaxing", "family_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.4)),
            ActivityItem(name="Heritage Walking Trail", category="outdoor_relaxed", cost=0, duration=90,
                attributes=ActivityAttributes(vibes=["cultural", "budget_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.70, rating=4.2)),
        ]
        sample_active = [
            ActivityItem(name="Adventure Trek Base Camp", category="outdoor_active", cost=25, duration=180,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning"], suitable_for_groups=True,
                    popularity_score=0.82, rating=4.5)),
            ActivityItem(name="Rock Climbing Center", category="outdoor_active", cost=28, duration=120,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.78, rating=4.3)),
            ActivityItem(name="Kayaking & Water Sports", category="outdoor_active", cost=22, duration=120,
                attributes=ActivityAttributes(vibes=["adventurous", "active"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.85, rating=4.6)),
            ActivityItem(name="Go-Kart Racing Arena", category="outdoor_active", cost=20, duration=60,
                attributes=ActivityAttributes(vibes=["adventurous", "social"],
                    time_slots=["afternoon", "evening"], suitable_for_groups=True,
                    popularity_score=0.88, rating=4.4)),
            ActivityItem(name="Cycling Trail Adventure", category="outdoor_active", cost=10, duration=120,
                attributes=ActivityAttributes(vibes=["active", "budget_friendly"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.75, rating=4.2)),
            ActivityItem(name="Paintball Combat Zone", category="outdoor_active", cost=28, duration=90,
                attributes=ActivityAttributes(vibes=["adventurous", "social"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.80, rating=4.3)),
            ActivityItem(name="Horseback Riding Stables", category="outdoor_active", cost=35, duration=90,
                attributes=ActivityAttributes(vibes=["adventurous", "relaxing"],
                    time_slots=["morning", "afternoon"], suitable_for_groups=True,
                    popularity_score=0.72, rating=4.4)),
            ActivityItem(name="Public Sports Ground", category="outdoor_active", cost=0, duration=90,
                attributes=ActivityAttributes(vibes=["active", "budget_friendly"],
                    time_slots=["morning", "afternoon", "evening"], suitable_for_groups=True,
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
        time_slot_votes = defaultdict(int)
        dietary_votes = defaultdict(int)
        energy_levels = []
        exploration_factors = []
        vetoes = {"genres": set(), "cuisines": set(), "categories": set()}
        
        for pref in member_preferences:
            for g in pref.get("genres", []):
                genre_votes[g.lower().replace("-", "")] += 1
            for c in pref.get("cuisines", []):
                cuisine_votes[c.lower().replace(" ", "_")] += 1
            for v in pref.get("vibes", []):
                vibe_votes[v.lower().replace("-", "_")] += 1
                
            for g in pref.get("disliked_genres", []):
                vetoes["genres"].add(g.lower().replace("-", ""))
            for c in pref.get("disliked_cuisines", []):
                vetoes["cuisines"].add(c.lower().replace(" ", "_"))
            for cat in pref.get("disliked_categories", []):
                vetoes["categories"].add(cat.lower())
            budget = pref.get("budget_range", "medium")
            budget_votes[budget] += 1
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
        res_genres = [g for g in top_borda(genre_scores, 5) if g not in vetoes["genres"]]
        res_cuisines = [c for c in top_borda(cuisine_scores, 5) if c not in vetoes["cuisines"]]
        res_vibes = top_borda(vibe_scores, 3)
        res_times = top_borda(time_scores, 2) or ["afternoon", "evening"]
        
        return {
            "genres": res_genres,
            "cuisines": res_cuisines,
            "vibes": res_vibes,
            "budget_range": budget,
            "preferred_time_slots": res_times,
            "dietary_restrictions": dietary,
            "exploration_factor": avg_exploration,
            "energy_level": round(avg_energy, 1),
            "member_count": n_members,
            "vetoes": {k: list(v) for k, v in vetoes.items()}
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
            1.0 if 5 <= h < 12 else 0.0,
            1.0 if 12 <= h < 17 else 0.0,
            1.0 if 17 <= h < 21 else 0.0,
            1.0 if h >= 21 or h < 5 else 0.0,
            1.0 if 5 <= h < 12 else 0.0,
            1.0 if 12 <= h < 17 else 0.0,
            1.0 if 17 <= h < 21 else 0.0,
            1.0,
            0.0,
            0.0,
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
        return max(5, int((dist_km / TRAVEL_SPEED_KMH) * 60) + 5)
    
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
    
    def _is_similar(self, name1: str, name2: str) -> bool:
        s1 = re.sub(r'[^a-zA-Z0-0]', '', name1.lower())
        s2 = re.sub(r'[^a-zA-Z0-9]', '', name2.lower())
        if s1 == s2: return True
        if s1 in s2 or s2 in s1:
            if abs(len(s1) - len(s2)) < 5: return True
        return False

    def build(
        self,
        pool: Dict[str, List[ActivityItem]],
        context: Dict,
        start_min: int,
        end_min: int,
        centroid: Tuple[float, float],
        group_prefs: Dict,
        exclusion_set: set,
        adjustment_context: str = "",
        category_bias: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        category_bias = category_bias or {}
        base_budget = float(MAX_BUDGET_MAP.get(context.get("budget", "medium"), 1500))
        member_count = group_prefs.get("member_count", 1)
        max_spend = base_budget * member_count

        span = max(end_min - start_min, 1)
        
        logger.info(
            f"[ItineraryBuilder] Building for {start_min}-{end_min}, group_size={member_count}, total_budget={max_spend}"
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

                    vetoes = group_prefs.get("vetoes", {})
                    if category.lower() in [v.lower() for v in vetoes.get("categories", [])]:
                        continue

                    div_count = node.diversity.get(category, 0)
                    diversity_penalty = (div_count**2) * 4.0
                    
                    if node.schedule and node.schedule[-1]["category"] == category:
                        continue
                    
                    is_solo = group_prefs.get("member_count", 1) <= 1
                    
                    for item in items:
                        if any(self._is_similar(item.name, prev["venue"]) for prev in node.schedule):
                            continue
                        if item.name in node.exclusion: continue
                        
                        if is_solo and item.attributes.solo_score < 0.4:
                            continue
                        
                        if any(g.lower() in [v.lower() for v in vetoes.get("genres", [])] for g in item.attributes.genres):
                            continue
                        if any(c.lower() in [v.lower() for v in vetoes.get("cuisines", [])] for c in item.attributes.cuisines):
                            continue

                        if max_spend > 0 and node.spent + item.cost > max_spend:
                            continue

                        lat = item.lat if item.lat != 0.0 else centroid[0]
                        lon = item.lon if item.lon != 0.0 else centroid[1]
                        dist = GeoEngine.haversine(centroid[0], centroid[1], lat, lon)
                        travel = self._travel_time(dist)
                        
                        if node.current_time + travel + item.duration > end_min:
                            continue

                        base_score = self.bandit.score_item(item, time_context, group_prefs)

                        dist_penalty = (dist / 12.0) ** 1.2
                        
                        target_energy_level = group_prefs.get("energy_level", 3.0)
                        item_energy_str = item.attributes.energy_profile

                        e_map = {"low": 1.0, "medium": 3.0, "high": 5.0}
                        item_energy_val = e_map.get(item_energy_str, 3.0)

                        if dp < 0.3:
                            ideal_flow_val = 2.0
                        elif dp > 0.7:
                            ideal_flow_val = 1.5
                        else:
                            ideal_flow_val = target_energy_level

                        energy_match = 1.0 - abs(ideal_flow_val - item_energy_val) / 5.0
                        
                        budget_tier = context.get("budget", "medium")
                        if budget_tier in ["medium", "high"]:
                            cost_score = (item.cost / max_spend) * 0.3
                        else:
                            cost_score = -(item.cost / (max_spend + 1)) * 0.7
                        
                        solo_bonus = (item.attributes.solo_score * 4.0) if is_solo else 0.0

                        time_match = self.matcher.compute_time_match(time_slot, item.attributes.time_slots)

                        breather_penalty = 0.0
                        if node.schedule and node.schedule[-1].get("energy_profile") == "high" and item_energy_str == "high":
                            breather_penalty = 10.0
                            logger.debug(f"[Engine] Applying breather penalty for {item.name}")
                        
                        meal_window_penalty = 0.0
                        arrival_h_float = (node.current_time + travel) / 60.0
                        if category != "dining":
                            if 12.5 <= arrival_h_float <= 13.5:
                                meal_window_penalty = 15.0
                            elif 19.8 <= arrival_h_float <= 21.0:
                                meal_window_penalty = 20.0

                        seq_bonus = 0.0
                        if category == "dining":
                            if node.schedule and node.schedule[-1]["category"] != "dining":
                                seq_bonus += 2.0
                            arrival_h = (node.current_time + travel) // 60
                            if 11 <= arrival_h <= 14:
                                if time_since_meal > 150:
                                    seq_bonus += 20.0
                            elif 18 <= arrival_h <= 21:
                                if time_since_meal > 200:
                                    seq_bonus += 25.0
                            elif time_since_meal > 300:
                                seq_bonus += 5.0
                        
                        adj_bonus = 0.0
                        if adjustment_context:
                            adj_lower = adjustment_context.lower()
                            if ("movie" in adj_lower or "cinema" in adj_lower) and category == "movie":
                                adj_bonus = 50.0
                            elif ("eat" in adj_lower or "dine" in adj_lower) and category == "dining":
                                adj_bonus = 10.0
                        
                        bias_multiplier = category_bias.get(category, 1.0)
                        
                        oscillation_penalty = 0.0
                        if len(node.schedule) >= 3:
                            recent_cats = [s["type"] for s in node.schedule[-3:]]
                            if category in recent_cats:
                                oscillation_penalty = 5.0

                        total_score = ((base_score * bias_multiplier) * 0.3) + (seq_bonus * 0.4) + (energy_match * 0.3) + \
                                     (cost_score * 0.1) - dist_penalty - (diversity_penalty * 0.8) - \
                                     oscillation_penalty - breather_penalty - meal_window_penalty + \
                                     adj_bonus + solo_bonus

                        if time_match < 0.3:
                            continue

                        arrival = node.current_time + travel
                        
                        if category == "movie":
                            valid_slots = item.attributes.exact_start_times if item.attributes.exact_start_times else [arrival]
                            if not valid_slots or valid_slots[0] == arrival:
                                movie_slots = [630, 810, 990, 1170, 1350]
                                next_slot = next((s for s in movie_slots if s >= arrival), None)
                            else:
                                valid_slots = sorted(valid_slots)
                                next_slot = next((s for s in valid_slots if s >= arrival), None)
                                
                            if not next_slot:
                                continue
                            wait_time = next_slot - arrival
                            if wait_time > 120:
                                continue
                            total_score -= (wait_time * 0.4)
                            arrival = next_slot

                        new_node = node.clone()
                        departure = arrival + item.duration
                        
                        arrival_time_str = f"{arrival // 60:02d}:{arrival % 60:02d}"
                        departure_time_str = f"{departure // 60:02d}:{departure % 60:02d}"
                        arrival_h_f = arrival / 60.0

                        if travel > 0:
                            travel_note = f"~{travel} min drive from previous stop"
                        else:
                            travel_note = "Same area — no travel needed"

                        meal_label = get_meal_label(arrival_h_f) if category == "dining" else ""

                        entry = {
                            **item.to_dict(),
                            "activity": item.attributes.action_title if item.attributes.action_title else item.name,
                            "venue": item.name,
                            "type": category,
                            "arrival_time": arrival_time_str,
                            "departure_time": departure_time_str,
                            "time_slot_display": f"{arrival_time_str} - {departure_time_str}",
                            "duration_minutes": item.duration,
                            "estimated_cost": item.cost,
                            "distance_km": round(dist, 2),
                            "travel_time_min": travel,
                            "travel_note": travel_note,
                            "meal_label": meal_label,
                            "score": total_score,
                            "order": len(node.schedule) + 1
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
                    free_duration = min(60, end_min - node.current_time)
                    if free_duration >= 20:
                        ft_start = node.current_time
                        ft_end = ft_start + free_duration
                        ft_start_str = f"{ft_start // 60:02d}:{ft_start % 60:02d}"
                        ft_end_str   = f"{ft_end // 60 :02d}:{ft_end % 60 :02d}"
                        time_slot_label = self._get_time_slot(ft_start)
                        suggestions = {
                            "morning":   ["Window shopping", "Photography walk", "Grab a snack", "Explore the neighbourhood"],
                            "afternoon": ["People watching at a café", "Browse a bookstore", "Street food hunt", "Take photos"],
                            "evening":   ["Sunset walk", "Grab a chai", "Explore local market", "Chill at a viewpoint"],
                            "night":     ["Night food walk", "Rooftop spotting", "Dessert hunt", "Explore the nightlife area"],
                        }.get(time_slot_label, ["Explore freely", "Grab a snack", "Rest and recharge"])
                        free_entry = {
                            "activity": "Free Time — Explore on Your Own",
                            "venue": "Open Area",
                            "type": "free_time",
                            "category": "free_time",
                            "is_free_time": True,
                            "arrival_time": ft_start_str,
                            "departure_time": ft_end_str,
                            "time_slot_display": f"{ft_start_str} - {ft_end_str}",
                            "duration_minutes": free_duration,
                            "estimated_cost": 0,
                            "travel_time_min": 0,
                            "travel_note": "",
                            "meal_label": "",
                            "distance_km": 0,
                            "score": 0,
                            "source": "system",
                            "description": f"No perfect match found for this {free_duration}-min window. Use this time to explore freely or rest.",
                            "suggestions": suggestions,
                            "order": len(node.schedule) + 1
                        }
                        node.schedule.append(free_entry)
                        node.current_time = ft_end
                        new_candidates.append(node)
                    else:
                        final_itineraries.append(node)

            if not new_candidates:
                break

            new_candidates.sort(key=lambda x: x.score, reverse=True)
            beam = new_candidates[:beam_width]

        if not final_itineraries and not beam:
            return []
            
        all_final = final_itineraries + beam
        best_overall = max(all_final, key=lambda x: x.score)
        
        total_live = sum(1 for s in best_overall.schedule if s.get("source") not in ("sample",))
        coverage = (total_live / len(best_overall.schedule)) * 100 if best_overall.schedule else 0
        enjoyment_score = round(best_overall.score / (len(best_overall.schedule) or 1), 2)
        
        logger.info(
            f"[Engine] OVERHAUL COMPLETE: Enjoyment={enjoyment_score}, Live Coverage={coverage}% ({total_live}/{len(best_overall.schedule)})"
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
        self._generation_locks: Dict[str, asyncio.Lock] = {}
        self._generation_cache: Dict[str, Tuple[Dict, float]] = {}
        self._cache_ttl = 45.0
    
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
        city: str,
        categories: List[str],
        group_prefs: Dict,
    ) -> Dict[str, List[ActivityItem]]:
        pool: Dict[str, List[ActivityItem]] = {cat: [] for cat in ACTIONS}
        
        category_to_task = {}
        
        if "dining" in categories:
            category_to_task["dining"] = self.web_fetcher.search_restaurants(
                lat, lon, group_prefs.get("cuisines", []), 
                group_prefs.get("budget_range", "medium")
            )
        
        if "movie" in categories:
            category_to_task["movie"] = self.web_fetcher.search_movies(
                lat, lon, city, group_prefs.get("genres", [])
            )
        
        if "entertainment" in categories:
            category_to_task["entertainment"] = self.web_fetcher.search_events(
                lat, lon, "entertainment"
            )
        
        if "cultural" in categories:
            category_to_task["cultural"] = self.web_fetcher.search_events(
                lat, lon, "cultural"
            )
        
        if "outdoor_relaxed" in categories:
            category_to_task["outdoor_relaxed"] = self.web_fetcher.search_outdoor_activities(
                lat, lon, "outdoor_relaxed", group_prefs.get("vibes", [])
            )
        
        if "outdoor_active" in categories:
            category_to_task["outdoor_active"] = self.web_fetcher.search_outdoor_activities(
                lat, lon, "outdoor_active", group_prefs.get("vibes", [])
            )

        active_cats = list(category_to_task.keys())
        tasks = [category_to_task[cat] for cat in active_cats]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cat_to_live_items = {}
        for cat, result in zip(active_cats, results):
            if isinstance(result, list) and len(result) > 0:
                live_items = [item for item in result if item.source not in ("sample",)]
                if live_items:
                    cat_to_live_items[cat] = live_items

        if not cat_to_live_items and len(categories) > 0:
            logger.info("[Fetch] Zero live results. Triggering aggressive recovery scan...")
            recovery_cat = categories[0]
            recovery_items = await self.web_fetcher._search_selenium_fallback(recovery_cat, lat, lon)
            if recovery_items:
                cat_to_live_items[recovery_cat] = recovery_items
        
        has_any_live = len(cat_to_live_items) > 0

        for cat in active_cats:
            if has_any_live:
                if cat in cat_to_live_items:
                    items = cat_to_live_items[cat]
                    for item in items:
                        item.source = "live"
                    pool[cat] = items
                    logger.info(f"[Fetch] {cat}: {len(items)} LIVE items fetched.")
                else:
                    pool[cat] = []
                    logger.warning(f"[Fetch] {cat}: No live data. Skipping to ensure 100% live itinerary.")
            else:
                samples = self._get_sample_for_category(cat, group_prefs)
                for item in samples:
                    item.source = "sample"
                pool[cat] = samples
                logger.warning(f"[Fetch] {cat}: No live data globally — using {len(samples)} sample items.")
        
        weather_score = group_prefs.get("weather_score", 0.7)
        if weather_score < 0.4:
            logger.info(f"[Engine] Poor weather ({weather_score:.2f}). Deprioritizing outdoor activities.")
            if "outdoor_relaxed" in pool:
                for item in pool["outdoor_relaxed"]: item.attributes.popularity_score *= 0.5
            if "outdoor_active" in pool:
                for item in pool["outdoor_active"]: item.attributes.popularity_score *= 0.3
        
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
    
    async def _enrich_schedule_with_llm(
        self, schedule: List[Dict], city: str, constraints: Dict, group_prefs: Dict, missing_cats: List[str] = None
    ):
        if not schedule:
            return "", ""

        for s in schedule:
            s["description"] = self._generate_core_description(s, city, group_prefs)
            
        prompt = (
            f"You are a local guide in {city}. Provide a warm, engaging summary of this itinerary and "
            f"the logic behind why it's perfect for this group.\n"
            f"Itinerary: " + ", ".join([s['venue'] for s in schedule]) + "\n"
            "Return JSON: {'summary': 'paragraph', 'reasoning': 'paragraph'}"
        )
        
        models = ["z-ai/glm-4.5-air:free"]
        key = os.environ.get("OPENROUTER_API_KEY", "")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": models[0],
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=20.0
                )
                if resp.status_code == 200:
                    data = json.loads(resp.json()["choices"][0]["message"]["content"])
                    return data.get("summary", ""), data.get("reasoning", "")
                elif resp.status_code == 429:
                    logger.info("[LLM] OpenRouter rate limit reached (429). Jumping to fallback.")
            except Exception as e:
                logger.info(f"[LLM] Narrative generation (external limit/error): {e}")
        
        return self._generate_fallback_summary(schedule, city, group_prefs)
        
        logger.warning("[LLM] AI attempts failed — using fallback descriptions.")
        fallbacks = [
            "Experience the unique atmosphere and local charm of {venue} during this {type} activity.",
            "Take some time to explore {venue}, a perfect spot for {type} in the heart of {city}.",
            "Make the most of your day with a visit to {venue}, known for its {type} vibes.",
            "A wonderful opportunity to enjoy {type} at {venue} with your group.",
            "Discover what makes {venue} special as you enjoy this {type} session together.",
            "Immerse yourselves in the {type} experience at the local favorite {venue}.",
            "Get a true sense of the city's {type} scene with a tailored visit to {venue}.",
            "Enjoy some quality time at {venue}, a top-rated destination for {type}."
        ]
        
        for i, s in enumerate(schedule):
            template = fallbacks[i % len(fallbacks)]
            s["description"] = template.format(
                venue=s['venue'], 
                type=s['type'].replace('_', ' '),
                city=city
            )
    
    def _generate_core_description(self, item: Dict, city: str, group_prefs: Dict) -> str:
        cat = item.get("type", "default")
        templates = SIGNATURE_VIBE_TEMPLATES.get(cat, SIGNATURE_VIBE_TEMPLATES["default"])
        template = random.choice(templates)
        
        cuisine = " / ".join(item.get("attributes", {}).get("cuisines", [])) or "local"
        vibe = " / ".join(item.get("attributes", {}).get("vibes", [])) or "welcoming"
        
        return template.format(
            venue=item.get("venue", "this spot"),
            city=city,
            cuisine=cuisine,
            vibe=vibe
        )

    async def _parse_adjustment_request(self, user_text: str) -> Dict[str, Any]:
        prompt = (
            f"A user wants to adjust their travel itinerary with the following request: \"{user_text}\"\n"
            "Translate this into a JSON object with strictly these keys:\n"
            "1. 'category_bias': Dict mapping categories (dining, movie, cultural, entertainment, outdoor_relaxed, outdoor_active) to float weights (1.0 default, 2.0 for boost, 0.5 for avoid)\n"
            "2. 'energy_limit': 'low', 'medium', or 'high'\n"
            "3. 'is_solo_preference': boolean\n"
            "4. 'specific_intent': a short string summarizing the new vibe.\n"
            "Return ONLY the JSON object."
        )
        
        key = os.environ.get("OPENROUTER_API_KEY", "")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": "z-ai/glm-4.5-air:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=10.0
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(content)
                elif resp.status_code == 429:
                    logger.info("[LLM] OpenRouter rate limit reached (429). Jumping to keyword-based fallback.")
            except Exception as e:
                logger.info(f"[LLM] Adjustment parsing (external limit/error): {e}")
        
        text = user_text.lower()
        bias = {}
        if "movie" in text or "cinema" in text or "film" in text or "watch" in text:
            bias["movie"] = 3.0
            bias["outdoor_relaxed"] = 0.1
            bias["outdoor_active"] = 0.1
        if "park" in text or "walk" in text or "nature" in text or "nature" in text:
            bias["outdoor_relaxed"] = 2.0
            bias["movie"] = 0.5
        if "eat" in text or "food" in text or "hungry" in text or "lunch" in text or "dinner" in text or "restaurant" in text or "cafe" in text:
            bias["dining"] = 2.5
        if "fun" in text or "game" in text or "active" in text or "play" in text or "sport" in text or "arcade" in text:
            bias["entertainment"] = 2.0
            bias["outdoor_active"] = 2.0
            
        energy = "medium"
        if "chill" in text or "relax" in text or "tired" in text or "sit" in text:
            energy = "low"
        elif "active" in text or "hype" in text or "run" in text or "play" in text:
            energy = "high"
            
        return {"category_bias": bias, "energy_limit": energy, "is_solo_preference": "solo" in text or "alone" in text, "specific_intent": "keyword matched adjustment"}

    async def _audit_and_refine(self, schedule: List[Dict], group_prefs: Dict) -> Tuple[bool, Dict]:
        if not schedule: return True, {}
        
        lines = "\n".join([f"{s['arrival_time']}-{s['departure_time']}: {s['venue']} ({s['type']})" for s in schedule])
        prompt = (
            "Critique this daily itinerary for a group of people. Is it truly enjoyable and 'human-passable'?\n"
            "Check for: crazy pacing, back-to-back high energy, bad meal timing, excessive walking, or oscillation.\n"
            f"Itinerary:\n{lines}\n"
            "Return JSON exactly like this:\n"
            "{\n"
            "  \"is_passable\": boolean,\n"
            "  \"score_out_of_10\": int,\n"
            "  \"feedback\": \"one sentence explanation\",\n"
            "  \"category_bias\": {\"outdoor_active\": 0.3, \"dining\": 1.5},\n"
            "  \"energy_limit\": float\n"
            "}"
        )
        
        key = os.environ.get("OPENROUTER_API_KEY", "")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": "z-ai/glm-4.5-air:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = json.loads(resp.json()["choices"][0]["message"]["content"])
                    logger.info(f"[Critic] {data.get('score_out_of_10')}/10 - {data.get('feedback')}")
                    if not data.get("is_passable", True):
                        logger.info(f"[Critic] Applying overrides to Engine: {data.get('category_bias', {})}")
                    return data.get("is_passable", True), data
            except Exception as e:
                logger.warning(f"[Critic] Logic audit failed: {e}")
        
        return True, {}
    
    def _generate_fallback_summary(self, schedule: List[Dict], city: str, group_prefs: Dict) -> Tuple[str, str]:
        if not schedule:
            return (
                "No activities could be scheduled.",
                "The constraints were too tight or no venues were found nearby."
            )
        cats = list({s['type'] for s in schedule})
        total_cost = sum(float(s.get('estimated_cost', 0)) for s in schedule)
        first = schedule[0]
        last = schedule[-1]
        start_t = first.get('arrival_time', '?')
        end_t = last.get('departure_time', '?')
        energy = group_prefs.get('energy_level', 3)
        energy_desc = 'relaxed' if energy <= 2 else ('high-energy' if energy >= 4 else 'balanced')
        vibes = group_prefs.get('vibes', ['social'])
        vibe_str = ' and '.join(vibes[:2]) if vibes else 'social'
        budget = group_prefs.get('budget_range', 'medium')
        
        cat_friendly = {
            'dining': 'dining', 'movie': 'cinema', 'outdoor_relaxed': 'outdoor relaxation',
            'outdoor_active': 'active outdoor fun', 'cultural': 'cultural exploration',
            'entertainment': 'entertainment'
        }
        cat_names = [cat_friendly.get(c, c) for c in cats]
        
        summary = (
            f"Your {len(schedule)}-stop itinerary in {city} kicks off at {start_t} and wraps up at {end_t}, "
            f"blending {', '.join(cat_names[:-1]) + ' and ' + cat_names[-1] if len(cat_names) > 1 else cat_names[0]}. "
            f"The total spend comes to approximately ₹{total_cost:.0f} per person — perfect for a {budget}-budget outing."
        )
        reasoning = (
            f"This {energy_desc} plan was built to match your {vibe_str} preferences within a {budget} budget. "
            f"Activities are sequenced so the day flows naturally from {start_t} to {end_t}, "
            f"with meals timed around your energy windows and travel kept short between stops. "
            f"Every venue was chosen from {'live local data' if any(s.get('source') == 'live' for s in schedule) else 'curated recommendations'} "
            f"to give you a genuine, do-able plan you can actually enjoy."
        )
        return summary, reasoning

    def _get_llm(self):
        return True
    
    async def generate_recommendation(
        self, group_id: str, adjustment_context: Optional[str] = None
    ) -> Dict[str, Any]:
        if adjustment_context is None:
            cached = self._generation_cache.get(group_id)
            if cached:
                result, ts = cached
                age = datetime.now(timezone.utc).timestamp() - ts
                if age < self._cache_ttl:
                    logger.info(f"[Engine] Returning cached recommendation for group {group_id} (age={age:.1f}s)")
                    return result
        
        if group_id not in self._generation_locks:
            self._generation_locks[group_id] = asyncio.Lock()
        lock = self._generation_locks[group_id]
        
        async with lock:
            if adjustment_context is None:
                cached = self._generation_cache.get(group_id)
                if cached:
                    result, ts = cached
                    if datetime.now(timezone.utc).timestamp() - ts < self._cache_ttl:
                        return result
            return await self._generate_recommendation_impl(group_id, adjustment_context)
    
    async def _generate_recommendation_impl(
        self, group_id: str, adjustment_context: Optional[str] = None
    ) -> Dict[str, Any]:
        group = await self.db.group_sessions.find_one({"id": group_id}, {"_id": 0})
        if not group:
            raise ValueError("Group not found")
        
        constraints = group.get("constraints", {})
        start_min = self._parse_time(constraints.get("start_time", "09:00"))
        end_min = self._parse_time(constraints.get("end_time", "21:00"))
        budget = constraints.get("budget_range", "medium")
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
        group_prefs["member_count"] = group_size

        if budget:
            group_prefs["budget_range"] = budget
        group_prefs["weather_score"] = weather_score
        logger.info(f"[Engine] Group prefs (including weather): {group_prefs}")

        registered_user_ids = [
            m["id"] for m in group.get("members", [])
            if not m["id"].startswith("guest_")
        ]
        memory_bias: Dict[str, float] = {}
        if registered_user_ids:
            try:
                mem_docs = await self.db.user_preference_memory.find(
                    {"user_id": {"$in": registered_user_ids}}
                ).to_list(20)
                liked_counts: Dict[str, int] = defaultdict(int)
                disliked_counts: Dict[str, int] = defaultdict(int)
                for doc in mem_docs:
                    for cat in doc.get("liked_categories", []):
                        liked_counts[cat] += 1
                    for cat in doc.get("disliked_categories", []):
                        disliked_counts[cat] += 1
                for cat in set(list(liked_counts.keys()) + list(disliked_counts.keys())):
                    likes = liked_counts.get(cat, 0)
                    dislikes = disliked_counts.get(cat, 0)
                    total = likes + dislikes
                    if total > 0:
                        ratio = likes / total
                        memory_bias[cat] = round(0.3 + ratio * 1.7, 2)
                if memory_bias:
                    logger.info(f"[Engine] User memory bias applied: {memory_bias}")
            except Exception as e:
                logger.warning(f"[Engine] Could not load user preference memory: {e}")

        alpha = float(group_prefs.get("exploration_factor", 1.5))
        self.bandit.set_alpha(alpha)
        logger.info(f"[Engine] RL Alpha set to {alpha}")

        allowed_cats = list(ACTIONS)

        if adjustment_context:
            adj_lower = adjustment_context.lower()
            if "movie" in adj_lower or "cinema" in adj_lower or "film" in adj_lower:
                if "movie" not in allowed_cats: allowed_cats.append("movie")
                group_prefs["genres"] = group_prefs.get("genres", []) + ["action", "drama", "comedy"]
            if "eat" in adj_lower or "food" in adj_lower or "restaurant" in adj_lower or "dine" in adj_lower:
                if "dining" not in allowed_cats: allowed_cats.append("dining")
            if "active" in adj_lower or "outdoor" in adj_lower or "park" in adj_lower:
                if "outdoor_active" not in allowed_cats: allowed_cats.append("outdoor_active")
                if "outdoor_relaxed" not in allowed_cats: allowed_cats.append("outdoor_relaxed")
            if "culture" in adj_lower or "museum" in adj_lower:
                if "cultural" not in allowed_cats: allowed_cats.append("cultural")

        pool = await self._fetch_activities(centroid[0], centroid[1], city_name, allowed_cats, group_prefs)

        context = {
            "budget": budget,
            "group_size": group_size,
            "weather_score": weather_score,
            "is_weekend": is_weekend,
        }

        adjustment_bias = {}
        if adjustment_context:
            logger.info(f"[Engine] Processing adjustment: {adjustment_context}")
            adj_data = await self._parse_adjustment_request(adjustment_context)
            adjustment_bias = adj_data.get("category_bias", {})
            group_prefs["energy_level"] = {"low": 1.0, "medium": 3.0, "high": 5.0}.get(adj_data.get("energy_limit"), 3.0)
            logger.info(f"[Engine] Intent: {adj_data.get('specific_intent')}")

        merged_bias = {**memory_bias}
        for cat, mult in adjustment_bias.items():
            merged_bias[cat] = merged_bias.get(cat, 1.0) * mult

        final_schedule: List[Dict] = []
        exclusion_set: set = set()
        days = vac_days if is_vac else 1
        
        attempts = 0
        while attempts < 2:
            attempts += 1
            current_schedule = []
            for day in range(days):
                day_pool = {cat: list(items) for cat, items in pool.items()}
                daily = self.builder.build(
                    day_pool, context, start_min, end_min,
                    centroid, group_prefs, exclusion_set,
                    adjustment_context=adjustment_context,
                    category_bias=merged_bias
                )
                for item in daily: item["day"] = day + 1
                current_schedule.extend(daily)
            
            is_passable, correction_data = await self._audit_and_refine(current_schedule, group_prefs)
            if is_passable or attempts >= 2:
                final_schedule = current_schedule
                break
            else:
                logger.info(f"[Engine] Audit failed. Retrying with explicit structured biases...")
                ai_biases = correction_data.get("category_bias", {})
                for cat, v in ai_biases.items():
                    merged_bias[cat] = float(v)
                if "energy_limit" in correction_data:
                    group_prefs["energy_level"] = float(correction_data["energy_limit"])

        missing_requested = []
        if adjustment_context:
            adj_lower = adjustment_context.lower()
            requested_cats = {
                "movie": ["movie", "cinema", "film"],
                "dining": ["eat", "food", "restaurant", "dine"],
                "outdoor_active": ["active", "outdoor", "park"],
                "cultural": ["culture", "museum"]
            }
            for cat, keywords in requested_cats.items():
                if any(k in adj_lower for k in keywords):
                    if not any(s["type"] == cat for s in final_schedule):
                        missing_requested.append(cat)

        summary, reasoning = await self._enrich_schedule_with_llm(
            final_schedule, city_name, constraints, group_prefs, missing_requested
        )
        
        sources_used = list({s.get('source', 'sample') for s in final_schedule})
        has_live = 'live' in sources_used
        
        result = {
            "schedule": final_schedule,
            "summary": summary,
            "reasoning": reasoning,
            "diagnostics": {
                "city": city_name,
                "missing_requested": missing_requested,
                "weather_score": round(weather_score, 2),
                "data_source": "live" if has_live else "sample",
                "activity_count": len(final_schedule),
                "budget_tier": budget,
                "group_prefs": group_prefs,
                "centroid": {"lat": centroid[0], "lon": centroid[1]},
                "is_vacation": is_vac,
                "vacation_days": vac_days,
                "audit_attempts": attempts
            },
        }
        
        self._generation_cache[group_id] = (result, datetime.now(timezone.utc).timestamp())
        return result
    
    async def update_from_feedback(self, recommendation_id: str, feedback: Dict,
                                   source: str = "user_feedback"):
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
                logger.info(f"[RL] Updated arm={cat} reward={reward:.3f} source={source}")
            
            await self._save_model()

            if source == "user_feedback":
                user_ids = [
                    m["id"] for m in group.get("members", [])
                    if not m["id"].startswith("guest_")
                ]
                await self.update_user_preference_memory(user_ids, feedback)

        except Exception as exc:
            logger.warning(f"Feedback update error: {exc}")

    async def update_user_preference_memory(self, user_ids: List[str], feedback: Dict):
        liked = [
            r["category"] for r in feedback.get("activity_ratings", [])
            if r.get("score", 3) >= 4 and r.get("category") in ACTIONS
        ]
        disliked = [
            r["category"] for r in feedback.get("activity_ratings", [])
            if r.get("score", 3) <= 2 and r.get("category") in ACTIONS
        ]
        if not liked and not disliked:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        for uid in user_ids:
            try:
                await self.db.user_preference_memory.update_one(
                    {"user_id": uid},
                    {
                        "$push": {
                            "liked_categories":    {"$each": liked},
                            "disliked_categories": {"$each": disliked},
                        },
                        "$set":  {"updated_at": now_iso},
                        "$setOnInsert": {"user_id": uid, "created_at": now_iso},
                    },
                    upsert=True
                )
                logger.info(f"[Memory] Updated preference memory for user {uid}: liked={liked} disliked={disliked}")
            except Exception as e:
                logger.warning(f"[Memory] Could not update memory for {uid}: {e}")

__all__ = [
    "HybridRecommendationEngine",
    "ActivityItem",
    "ActivityAttributes",
    "ContextualThompsonEngine",
    "PreferenceMatcher",
    "GroupPreferenceAggregator",
]