from fastapi import FastAPI, APIRouter, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import os, uuid, random, string, logging, httpx, jwt, bcrypt

from rl_engine import HybridRecommendationEngine

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "groupsync_db")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGO = "HS256"
JWT_EXPIRE_MINUTES = 1440

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]
rl_engine = HybridRecommendationEngine(db)

app = FastAPI(title="GroupSync Recommendation API")
router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    default_preferences: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    default_preferences: Optional[Dict[str, Any]] = None
    created_at: str

class UserLogin(BaseModel):
    email: str
    password: str

class GroupSessionCreate(BaseModel):
    name: str
    start_date: str
    start_time: str
    end_time: str
    budget_range: Optional[str] = None

class GroupSessionUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    budget_range: Optional[str] = None

class GroupSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    creator_id: str
    invite_code: str
    status: str
    constraints: Dict[str, Any]
    members: List[Dict[str, Any]]
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

class StartSessionRequest(BaseModel):
    user_id: Optional[str] = None

class LocationData(BaseModel):
    lat: float
    lon: float
    user_id: Optional[str] = None

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_token(data: dict) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception:
        return None

async def current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return decode_token(authorization.replace("Bearer ", ""))

async def enrich_members(members: List[Dict]) -> List[Dict]:
    enriched = []
    for m in members:
        md = m.copy()
        if m["id"].startswith("guest_"):
            md["name"] = f"Guest {m['id'].split('_')[1][:4].upper()}"
            md["is_guest"] = True
        else:
            user = await db.users.find_one({"id": m["id"]}, {"name": 1})
            md["name"] = user.get("name", "Unknown") if user else "Unknown"
            md["is_guest"] = False
        enriched.append(md)
    return enriched

@router.post("/auth/register", response_model=UserResponse)
async def register(body: UserCreate):
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid, "email": body.email,
        "password": hash_password(body.password),
        "name": body.name, "default_preferences": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return UserResponse(id=uid, email=body.email, name=body.name,
                        default_preferences={}, created_at=doc["created_at"])

@router.post("/auth/login")
async def login(body: UserLogin):
    user = await db.users.find_one({"email": body.email}, {"_id": 0})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token({"user_id": user["id"], "email": user["email"]})
    return {"token": token, "user": {
        "id": user["id"], "email": user["email"],
        "name": user["name"],
        "default_preferences": user.get("default_preferences", {}),
    }}

@router.get("/users/me", response_model=UserResponse)
async def get_me(authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(404, "User not found")
    return UserResponse(**user)

@router.put("/users/me")
async def update_me(body: UserUpdate, authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    update = {}
    if body.name is not None:
        update["name"] = body.name
    if body.default_preferences is not None:
        update["default_preferences"] = body.default_preferences
    if not update:
        raise HTTPException(400, "No data provided")
    await db.users.update_one({"id": payload["user_id"]}, {"$set": update})
    return {"message": "Profile updated"}

@router.post("/groups", response_model=GroupSessionResponse)
async def create_group(body: GroupSessionCreate,
                       authorization: Optional[str] = Header(None)):
    user = await current_user(authorization)
    creator_id = user["user_id"] if user else f"guest_{str(uuid.uuid4())[:8]}"
    invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    gid = str(uuid.uuid4())
    schedule_display = f"{body.start_date} | {body.start_time} - {body.end_time}"
    doc = {
        "id": gid, "name": body.name, "creator_id": creator_id,
        "invite_code": invite_code, "status": "lobby",
        "constraints": {**body.model_dump(exclude={"name"}),
                        "schedule_display": schedule_display},
        "members": [{"id": creator_id, "role": "creator", "status": "joined",
                     "location": "", "location_name": ""}],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.group_sessions.insert_one(doc)
    return GroupSessionResponse(**{k: v for k, v in doc.items() if k != "_id"})

@router.put("/groups/{group_id}", response_model=GroupSessionResponse)
async def update_group(group_id: str, body: GroupSessionUpdate,
                       authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    group = await db.group_sessions.find_one({"id": group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    if group.get("creator_id") != payload["user_id"]:
        raise HTTPException(403, "Only creator can edit")
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "No data provided")
    if "name" in fields:
        await db.group_sessions.update_one(
            {"id": group_id}, {"$set": {"name": fields["name"]}}
        )
    constraint_updates = {
        "constraints." + f: fields[f]
        for f in ["start_date", "start_time", "end_time", "budget_range"]
        if f in fields
    }
    if constraint_updates:
        await db.group_sessions.update_one(
            {"id": group_id}, {"$set": constraint_updates}
        )
    updated = await db.group_sessions.find_one({"id": group_id}, {"_id": 0})
    return GroupSessionResponse(**updated)

@router.get("/groups/my")
async def get_my_groups(authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Login required")
    groups = await db.group_sessions.find(
        {"members.id": payload["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"groups": groups}

@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    group = await db.group_sessions.find_one({"id": group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    if group.get("creator_id") != payload["user_id"]:
        raise HTTPException(403, "Only creator can delete")
    await db.group_sessions.delete_one({"id": group_id})
    return {"message": "Group deleted"}

@router.post("/groups/{group_id}/quit")
async def quit_group(group_id: str, authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    group = await db.group_sessions.find_one({"id": group_id})
    if group and group.get("creator_id") == payload["user_id"]:
        raise HTTPException(400, "Creator cannot quit — delete the group instead")
    result = await db.group_sessions.update_one(
        {"id": group_id}, {"$pull": {"members": {"id": payload["user_id"]}}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Group or member not found")
    return {"message": "Left group successfully"}

@router.delete("/groups/{group_id}/members/{member_id}")
async def remove_member(group_id: str, member_id: str,
                        authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    group = await db.group_sessions.find_one({"id": group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    if group.get("creator_id") != payload["user_id"]:
        raise HTTPException(403, "Only creator can remove members")
    if member_id == payload["user_id"]:
        raise HTTPException(400, "Cannot remove yourself as creator")
    result = await db.group_sessions.update_one(
        {"id": group_id}, {"$pull": {"members": {"id": member_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Member not found")
    return {"message": "Member removed"}

@router.post("/groups/{group_id}/restart")
async def restart_group(group_id: str, authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    group = await db.group_sessions.find_one({"id": group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    if group.get("creator_id") != payload["user_id"]:
        raise HTTPException(403, "Only creator can restart")
    await db.group_sessions.update_one(
        {"id": group_id}, {"$set": {"status": "lobby"}}
    )
    await db.preferences.delete_many({"group_id": group_id})
    return {"message": "Group restarted", "status": "lobby"}

@router.get("/groups/{group_id}", response_model=GroupSessionResponse)
async def get_group(group_id: str):
    group = await db.group_sessions.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Group not found")
    return GroupSessionResponse(**group)

@router.post("/groups/{group_id}/location")
async def update_location(group_id: str, loc: LocationData,
                          authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    rid = payload["user_id"] if payload else loc.user_id
    if not rid:
        raise HTTPException(401, "Authentication required")
    location_name = "Unknown Location"
    try:
        async with httpx.AsyncClient(timeout=7.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"format": "jsonv2", "lat": loc.lat, "lon": loc.lon},
                headers={"User-Agent": "GroupSyncApp/2.0"},
            )
        if resp.status_code == 200:
            addr = resp.json().get("address", {})
            city = (addr.get("city") or addr.get("town")
                    or addr.get("village") or addr.get("county", ""))
            location_name = f"{city}, {addr.get('country', '')}".strip(", ")
    except Exception:
        pass
    result = await db.group_sessions.update_one(
        {"id": group_id, "members.id": rid},
        {"$set": {
            "members.$.location": {"lat": loc.lat, "lon": loc.lon},
            "members.$.location_name": location_name,
        }},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Group or member not found")
    return {"message": "Location updated", "location_name": location_name}

@router.post("/groups/join/{invite_code}")
async def join_group(invite_code: str, authorization: Optional[str] = Header(None)):
    group = await db.group_sessions.find_one(
        {"invite_code": invite_code}, {"_id": 0}
    )
    if not group:
        raise HTTPException(404, "Invalid invite code")
    payload = await current_user(authorization)
    member_id = payload["user_id"] if payload else f"guest_{str(uuid.uuid4())[:8]}"
    if any(m["id"] == member_id for m in group["members"]):
        return {"group_id": group["id"], "member_id": member_id,
                "status": "Already a member"}
    await db.group_sessions.update_one(
        {"id": group["id"]},
        {"$push": {"members": {
            "id": member_id, "role": "member", "status": "joined",
            "location": {"lat": 0, "lon": 0}, "location_name": "",
        }}},
    )
    return {"group_id": group["id"], "member_id": member_id,
            "status": "Joined successfully"}

@router.get("/groups/{group_id}/members")
async def get_members(group_id: str):
    group = await db.group_sessions.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Group not found")
    enriched = await enrich_members(group.get("members", []))
    prefs = await db.preferences.find(
        {"group_id": group_id}, {"_id": 0}
    ).to_list(100)
    submitted_ids = (
        {p.get("session_id") for p in prefs} | {p.get("user_id") for p in prefs}
    )
    members_out = [
        {**m, "preferences_submitted": m["id"] in submitted_ids}
        for m in enriched
    ]
    return {
        "members": members_out,
        "total": len(members_out),
        "submitted": sum(1 for m in members_out if m["preferences_submitted"]),
    }

@router.post("/preferences")
async def submit_preferences(body: PreferenceSubmit):
    if body.is_registered and body.user_id:
        user = await db.users.find_one({"id": body.user_id})
        if user and not user.get("default_preferences"):
            await db.users.update_one(
                {"id": body.user_id},
                {"$set": {"default_preferences": body.preferences}},
            )
    pref_query = {"group_id": body.group_id}
    if body.user_id:
        pref_query["user_id"] = body.user_id
    else:
        pref_query["session_id"] = body.session_id
    pid = str(uuid.uuid4())
    await db.preferences.update_one(
        pref_query,
        {
            "$set": {
                **body.model_dump(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "$setOnInsert": {"id": pid}
        },
        upsert=True
    )
    group = await db.group_sessions.find_one({"id": body.group_id}, {"_id": 0})
    if group:
        prefs = await db.preferences.find(
            {"group_id": body.group_id}
        ).to_list(100)
        reg_count = len([
            m for m in group.get("members", [])
            if not m["id"].startswith("guest_")
        ])
        if reg_count > 0 and len(prefs) >= reg_count:
            await db.group_sessions.update_one(
                {"id": body.group_id}, {"$set": {"status": "preferences"}}
            )
    return {"id": pid, "message": "Preferences submitted"}

@router.post("/recommendations", response_model=RecommendationResponse)
async def generate_recommendation(body: RecommendationRequest):
    group = await db.group_sessions.find_one({"id": body.group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Group not found")
    try:
        result = await rl_engine.generate_recommendation(body.group_id)
        rid = str(uuid.uuid4())
        doc = {
            "id": rid, "group_id": body.group_id,
            "schedule": result["schedule"],
            "diagnostics": result.get("diagnostics", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.recommendations.insert_one(doc)
        return RecommendationResponse(
            id=rid, group_id=body.group_id,
            schedule=result["schedule"],
            created_at=doc["created_at"],
        )
    except Exception as exc:
        logger.exception("Recommendation generation failed")
        raise HTTPException(500, f"Error generating recommendation: {exc}")

@router.get("/recommendations/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(rec_id: str):
    rec = await db.recommendations.find_one({"id": rec_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return RecommendationResponse(**rec)

@router.get("/recommendations/{rec_id}/diagnostics")
async def get_diagnostics(rec_id: str):
    rec = await db.recommendations.find_one({"id": rec_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec.get("diagnostics", {})

@router.post("/recommendations/replan")
async def replan(body: ReplanRequest):
    rec = await db.recommendations.find_one(
        {"id": body.recommendation_id}, {"_id": 0}
    )
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    await rl_engine.update_from_feedback(
        body.recommendation_id,
        {"overall_satisfaction": 2, "activity_ratings": [],
         "adjustment": body.adjustment},
        source="ai_replan",
    )
    result = await rl_engine.generate_recommendation(
        rec["group_id"], adjustment_context=body.adjustment
    )
    new_id = str(uuid.uuid4())
    new_doc = {
        "id": new_id, "group_id": rec["group_id"],
        "schedule": result["schedule"],
        "reasoning": f"Adjusted: {body.adjustment}. {result['reasoning']}",
        "parent_recommendation_id": body.recommendation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.recommendations.insert_one(new_doc)
    return {"id": new_id, "schedule": result["schedule"],
            "reasoning": new_doc["reasoning"]}

@router.post("/feedback")
async def submit_feedback(body: FeedbackSubmit):
    fid = str(uuid.uuid4())
    await db.feedback.insert_one({
        "id": fid, **body.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await rl_engine.update_from_feedback(body.recommendation_id, body.model_dump())
    await db.group_sessions.update_one(
        {"id": body.group_id},
        {"$set": {"status": "completed"},
         "$pull": {"members": {"id": {"$regex": "^guest_"}}}},
    )
    return {"id": fid, "message": "Thank you for your feedback!"}

@router.post("/groups/{group_id}/start")
async def start_session(group_id: str, body: StartSessionRequest,
                        authorization: Optional[str] = Header(None)):
    payload = await current_user(authorization)
    rid = payload["user_id"] if payload else body.user_id
    if not rid:
        raise HTTPException(401, "Authentication required")
    group = await db.group_sessions.find_one({"id": group_id})
    if not group:
        raise HTTPException(404, "Group not found")
    if group.get("creator_id") != rid:
        raise HTTPException(403, "Only the group creator can start the session")
    await db.group_sessions.update_one(
        {"id": group_id}, {"$set": {"status": "preferences"}}
    )
    return {"message": "Session started", "status": "preferences"}

@app.get("/")
async def root():
    return {"message": "GroupSync Recommendation API", "status": "running"}

app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await rl_engine.initialize()
    logger.info("RL engine ready")

@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()