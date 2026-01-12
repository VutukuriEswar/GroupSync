from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class UserLogin(BaseModel):
    email: str
    password: str

class GroupSessionCreate(BaseModel):
    name: str
    event_date: str
    start_time: str
    end_time: str
    indoor_outdoor: str
    budget_range: Optional[str] = None
    ott_subscriptions: Optional[List[str]] = None
    board_games: Optional[List[str]] = None

class GroupSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    creator_id: str
    invite_code: str
    status: str
    constraints: Dict[str, Any]
    members: List[Dict[str, str]]
    created_at: str

class PreferenceSubmit(BaseModel):
    group_id: str
    user_id: Optional[str] = None
    session_id: str
    preferences: Dict[str, Any]
    is_registered: bool

class RecommendationRequest(BaseModel):
    group_id: str

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    group_id: str
    schedule: List[Dict[str, Any]]
    reasoning: str
    created_at: str

class ReplanRequest(BaseModel):
    recommendation_id: str
    adjustment: str
    modified_schedule: Optional[List[Dict[str, Any]]] = None

class FeedbackSubmit(BaseModel):
    recommendation_id: str
    group_id: str
    overall_satisfaction: int
    activity_ratings: List[Dict[str, Any]]
    comments: Optional[str] = None