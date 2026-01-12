from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid
import random
import string
from typing import Optional

from models import (
    UserCreate, UserResponse, UserLogin,
    GroupSessionCreate, GroupSessionResponse,
    PreferenceSubmit, RecommendationRequest, RecommendationResponse,
    ReplanRequest, FeedbackSubmit
)
from auth import get_password_hash, verify_password, create_access_token, verify_token
from rl_engine import HybridRecommendationEngine

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize RL engine (Using the new Hybrid Engine)
rl_engine = HybridRecommendationEngine(db, os.environ.get('OPENROUTER_API_KEY'))

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Helper function to get current user from token
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    if not payload:
        return None
    return payload

# Auth routes
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hashed_password,
        "name": user_data.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        created_at=user_doc["created_at"]
    )

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
    }

@api_router.post("/groups", response_model=GroupSessionResponse)
async def create_group(group_data: GroupSessionCreate, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    creator_id = user["user_id"] if user else f"guest_{str(uuid.uuid4())[:8]}"
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    group_id = str(uuid.uuid4())
    
    schedule_display = f"{group_data.event_date} | {group_data.start_time} - {group_data.end_time}"
    
    group_doc = {
        "id": group_id,
        "name": group_data.name,
        "creator_id": creator_id,
        "invite_code": invite_code,
        "status": "lobby",
        "constraints": {
            **group_data.model_dump(exclude={"name"}),
            "schedule_display": schedule_display
        },
        "members": [
            {
                "id": creator_id, 
                "role": "creator", 
                "status": "joined",
                "location": ""
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.group_sessions.insert_one(group_doc)
    
    return GroupSessionResponse(
        id=group_id,
        name=group_data.name,
        creator_id=creator_id,
        invite_code=invite_code,
        status="lobby",
        constraints=group_doc["constraints"],
        members=group_doc["members"],
        created_at=group_doc["created_at"]
    )

@api_router.get("/groups/my")
async def get_my_groups(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    
    groups = await db.group_sessions.find(
        {"members.id": user["user_id"]}, 
        {"_id": 0}
    ).to_list(100)
    
    return {"groups": groups}

@api_router.get("/groups/{group_id}", response_model=GroupSessionResponse)
async def get_group(group_id: str):
    group = await db.group_sessions.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return GroupSessionResponse(**group)

@api_router.post("/groups/join/{invite_code}")
async def join_group(invite_code: str, authorization: Optional[str] = Header(None)):
    group = await db.group_sessions.find_one({"invite_code": invite_code}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    
    user = await get_current_user(authorization)
    member_id = user["user_id"] if user else f"guest_{str(uuid.uuid4())[:8]}"
    
    member_location = {"lat": 40.7128 + random.uniform(-0.05, 0.05), "lon": -74.0060 + random.uniform(-0.05, 0.05)}
    
    if any(m["id"] == member_id for m in group["members"]):
        return {"group_id": group["id"], "message": "Already a member"}
    
    await db.group_sessions.update_one(
        {"invite_code": invite_code},
        {"$push": {"members": {"id": member_id, "role": "member", "status": "joined", "location": member_location}}}
    )
    
    return {"group_id": group["id"], "message": "Successfully joined group"}

@api_router.get("/groups/{group_id}/members")
async def get_group_members(group_id: str):
    group = await db.group_sessions.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    preferences = await db.preferences.find({"group_id": group_id}, {"_id": 0}).to_list(100)
    submitted_ids = {p["session_id"] for p in preferences}
    
    members_with_status = []
    for member in group["members"]:
        members_with_status.append({
            **member,
            "preferences_submitted": member["id"] in submitted_ids or any(p.get("user_id") == member["id"] for p in preferences)
        })
    
    return {
        "members": members_with_status,
        "total": len(members_with_status),
        "submitted": len([m for m in members_with_status if m["preferences_submitted"]])
    }

@api_router.post("/preferences")
async def submit_preferences(preference_data: PreferenceSubmit):
    pref_id = str(uuid.uuid4())
    pref_doc = {
        "id": pref_id,
        **preference_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.preferences.insert_one(pref_doc)
    
    group = await db.group_sessions.find_one({"id": preference_data.group_id}, {"_id": 0})
    if group:
        prefs = await db.preferences.find({"group_id": preference_data.group_id}, {"_id": 0}).to_list(100)
        if len(prefs) >= len(group["members"]):
            await db.group_sessions.update_one(
                {"id": preference_data.group_id},
                {"$set": {"status": "ready"}}
            )
    
    return {"id": pref_id, "message": "Preferences submitted successfully"}

@api_router.post("/recommendations", response_model=RecommendationResponse)
async def generate_recommendation(req: RecommendationRequest):
    group = await db.group_sessions.find_one({"id": req.group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    try:
        result = await rl_engine.generate_recommendation(req.group_id)
        
        rec_id = str(uuid.uuid4())
        rec_doc = {
            "id": rec_id,
            "group_id": req.group_id,
            "schedule": result["schedule"],
            "reasoning": result["reasoning"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.recommendations.insert_one(rec_doc)
        
        return RecommendationResponse(
            id=rec_id,
            group_id=req.group_id,
            schedule=result["schedule"],
            reasoning=result["reasoning"],
            created_at=rec_doc["created_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendation: {str(e)}")

@api_router.get("/recommendations/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(rec_id: str):
    rec = await db.recommendations.find_one({"id": rec_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return RecommendationResponse(**rec)

@api_router.post("/recommendations/replan")
async def replan_recommendation(replan_data: ReplanRequest):
    rec = await db.recommendations.find_one({"id": replan_data.recommendation_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    await rl_engine.update_from_feedback(
        replan_data.recommendation_id,
        {"overall_satisfaction": 3} 
    )
    
    result = await rl_engine.generate_recommendation(rec["group_id"])
    
    new_rec_id = str(uuid.uuid4())
    new_rec_doc = {
        "id": new_rec_id,
        "group_id": rec["group_id"],
        "schedule": result["schedule"],
        "reasoning": f"Adjusted based on your feedback: {replan_data.adjustment}. {result['reasoning']}",
        "parent_recommendation_id": replan_data.recommendation_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.recommendations.insert_one(new_rec_doc)
    
    return {
        "id": new_rec_id,
        "schedule": result["schedule"],
        "reasoning": new_rec_doc["reasoning"]
    }

@api_router.post("/feedback")
async def submit_feedback(feedback_data: FeedbackSubmit):
    feedback_id = str(uuid.uuid4())
    feedback_doc = {
        "id": feedback_id,
        **feedback_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback_doc)
    
    await rl_engine.update_from_feedback(
        feedback_data.recommendation_id,
        feedback_data.model_dump()
    )
    
    await db.group_sessions.update_one(
        {"id": feedback_data.group_id},
        {"$set": {"status": "completed"}}
    )
    
    return {"id": feedback_id, "message": "Thank you for your feedback!"}

@api_router.get("/")
async def root():
    return {"message": "Group Recommendation Engine API", "status": "running"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()