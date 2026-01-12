import numpy as np
from typing import Dict, List, Any, Tuple
import random
import math
from datetime import datetime, timezone
import asyncio
import os
import json
from openai import AsyncOpenAI

class GeospatialEngine:
    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2) * math.sin(dLat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dLon / 2) * math.sin(dLon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def calculate_centroid(locations: List[Dict[str, float]]) -> Tuple[float, float]:
        if not locations: return 0, 0
        x = y = z = 0.0
        for loc in locations:
            lat = math.radians(loc['lat'])
            lon = math.radians(loc['lon'])
            x += math.cos(lat) * math.cos(lon)
            y += math.cos(lat) * math.sin(lon)
            z += math.sin(lat)
        x /= len(locations)
        y /= len(locations)
        z /= len(locations)
        central_lon = math.atan2(y, x)
        central_square_root = math.sqrt(x * x + y * y)
        central_lat = math.atan2(z, central_square_root)
        return math.degrees(central_lat), math.degrees(central_lon)

class HybridRecommendationEngine:
    def __init__(self, db, api_key: str):
        self.db = db
        self.geo = GeospatialEngine()
        
        self.bandit_state = {
            "movie": {"alpha": 1.0, "beta": 1.0},
            "dining": {"alpha": 1.0, "beta": 1.0},
            "outdoor_active": {"alpha": 1.0, "beta": 1.0},
            "outdoor_relaxed": {"alpha": 1.0, "beta": 1.0},
            "gaming": {"alpha": 1.0, "beta": 1.0},
            "cultural": {"alpha": 1.0, "beta": 1.0},
            "social_events": {"alpha": 1.0, "beta": 1.0},
        }
        
        self.llm_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
        self.model_name = "z-ai/glm-4.5-air:free"

    async def get_live_data(self, centroid_lat, centroid_lon, group_interests):
        live_activities = []
        
        if any("movie" in i.lower() for i in group_interests):
            live_activities.append({
                "name": "Dune: Part Two (Just Released)",
                "type": "movie",
                "venue": "Cineplex Downtown",
                "tags": ["sci-fi", "high_energy", "visual"],
                "lat": centroid_lat + 0.01, 
                "lon": centroid_lon + 0.01,
                "cost": 18,
                "duration": 166
            })

        if any("outdoor" in i.lower() or "social" in i.lower() for i in group_interests):
            live_activities.append({
                "name": "Spring Street Carnival (This Weekend)",
                "type": "social_events",
                "venue": "City Center Plaza",
                "tags": ["social", "high_energy", "food", "outdoor_relaxed"],
                "lat": centroid_lat - 0.005,
                "lon": centroid_lon - 0.005,
                "cost": 10,
                "duration": 180
            })
            
        return live_activities

    async def generate_recommendation(self, group_id: str) -> Dict[str, Any]:
        await self._load_bandit_state()
        group = await self.db.group_sessions.find_one({"id": group_id}, {"_id": 0})
        preferences = await self.db.preferences.find({"group_id": group_id}, {"_id": 0}).to_list(100)
        
        if not group or not preferences:
            raise ValueError("Missing data")

        group_profile = self._build_group_profile(preferences)
        
        member_locations = [m.get('location', {'lat': 0, 'lon': 0}) for m in group.get('members', [])]
        centroid = self.geo.calculate_centroid(member_locations)
        max_dist = max([self.geo.haversine(m['lat'], m['lon'], centroid[0], centroid[1]) for m in member_locations])
        
        base_activities = self._get_activity_database()
        live_activities = await self.get_live_data(centroid[0], centroid[1], group_profile['top_interests'])
        all_activities = base_activities + live_activities
        
        scored_activities = []
        for act in all_activities:
            content_score = self._calculate_similarity(group_profile['vector'], act['tags'])
            
            cat = act['type']
            rl_sample = np.random.beta(self.bandit_state[cat]['alpha'], self.bandit_state[cat]['beta'])
            
            act_dist = self.geo.haversine(centroid[0], centroid[1], act['lat'], act['lon'])
            distance_penalty = max(0, 1 - (act_dist / 20))
            
            if act['cost'] > group_profile['budget_limit']:
                continue
                
            final_score = (content_score * 0.6) + (rl_sample * 0.2) + (distance_penalty * 0.2)
            
            scored_activities.append({**act, "score": final_score, "distance": act_dist})
        scored_activities.sort(key=lambda x: x['score'], reverse=True)
        selected = scored_activities[:4]
        schedule = []
        current_time = 0
        for i, act in enumerate(selected):
            schedule.append({
                "order": i + 1,
                "activity": act["name"],
                "type": act["type"],
                "venue": act["venue"],
                "duration_minutes": act["duration"],
                "start_offset_minutes": current_time,
                "distance_km": round(act["distance"], 1),
                "estimated_cost": act["cost"],
                "reasoning_tag": f"Matched {act['type']} based on group interests"
            })
            current_time += act["duration"] + 30

        outlier_warning = ""
        if max_dist > 15:
            outlier_warning = f"Note: Some group members are further away. We prioritized a central meeting point to minimize travel imbalance."

        reasoning = await self._generate_reasoning(schedule, group_profile, outlier_warning)
        
        return {
            "schedule": schedule,
            "reasoning": reasoning,
            "centroid": centroid
        }

    def _build_group_profile(self, preferences):
        vectors = {
            "energy": 0, "social": 0, "budget_sensitivity": 0, 
            "outdoor": 0, "culture": 0, "food": 0
        }
        
        interests = []
        budget_limit = 50
        
        for p in preferences:
            prefs = p.get('preferences', {})
            if 'energy_level' in prefs: vectors['energy'] += prefs['energy_level']
            if 'social_preference' in prefs: 
                if prefs['social_preference'] == 'Party vibes': vectors['social'] += 2
                elif prefs['social_preference'] == 'Intimate group': vectors['social'] += 1
            if 'budget_sensitivity' in prefs: vectors['budget_sensitivity'] += prefs['budget_sensitivity']
            if 'genre_preferences' in prefs: interests.extend(prefs['genre_preferences'])
            if 'outdoor' in str(prefs).lower(): vectors['outdoor'] += 1

        count = len(preferences) or 1
        vector = {k: v/count for k, v in vectors.items()}
        
        return {
            "vector": vector,
            "top_interests": interests[:5],
            "budget_limit": budget_limit
        }

    def _calculate_similarity(self, user_vec, activity_tags):
        score = 0
        if 'high_energy' in activity_tags and user_vec['energy'] > 3: score += 1
        if 'low_energy' in activity_tags and user_vec['energy'] < 3: score += 1
        if 'social' in activity_tags and user_vec['social'] > 1.5: score += 1
        if 'outdoor' in activity_tags and user_vec['outdoor'] > 0.5: score += 1
        return score

    def _get_activity_database(self):
        return [
            {
                "name": "Sunset Yoga in the Park",
                "type": "outdoor_relaxed",
                "venue": "Central Park",
                "tags": ["low_energy", "outdoor", "wellness"],
                "lat": 40.7128, "lon": -74.0060,
                "cost": 0, "duration": 60
            },
            {
                "name": "Board Game Cafe Night",
                "type": "gaming",
                "venue": "Meeple Town",
                "tags": ["social", "low_energy", "indoor"],
                "lat": 40.7150, "lon": -74.0080,
                "cost": 15, "duration": 180
            },
            {
                "name": "Spicy Thai Dinner",
                "type": "dining",
                "venue": "Siam Palace",
                "tags": ["food", "social", "medium_energy"],
                "lat": 40.7130, "lon": -74.0070,
                "cost": 30, "duration": 90
            },
            {
                "name": "Escape Room: The Heist",
                "type": "gaming",
                "venue": "Escape NY",
                "tags": ["high_energy", "social", "problem_solving"],
                "lat": 40.7110, "lon": -74.0090,
                "cost": 35, "duration": 60
            }
        ]

    async def _generate_reasoning(self, schedule, profile, warning) -> str:
        try:
            summary = ", ".join([s['activity'] for s in schedule])
            prompt = f"We planned: {summary}. Group vibe: High Energy {profile['vector']['energy']}, Social {profile['vector']['social']}. {warning} Explain enthusiastically."
            
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return "This plan balances your group's love for social interaction with your budget constraints!"

    async def _load_bandit_state(self):
        state = await self.db.rl_model_state.find_one({"model_type": "hybrid_bandit"})
        if state:
            self.bandit_state = state["state"]

    async def update_from_feedback(self, recommendation_id: str, feedback: Dict):
        rec = await self.db.recommendations.find_one({"id": recommendation_id})
        if not rec: return
        
        reward = (feedback["overall_satisfaction"] - 1) / 4.0
        
        for act in rec.get("schedule", []):
            cat = act.get("type", "gaming")
            if cat in self.bandit_state:
                self.bandit_state[cat]["alpha"] += reward
                self.bandit_state[cat]["beta"] += (1 - reward)
                
        await self.db.rl_model_state.update_one(
            {"model_type": "hybrid_bandit"},
            {"$set": {"state": self.bandit_state, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )

RLRecommendationEngine = HybridRecommendationEngine