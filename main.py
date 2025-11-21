import os
from typing import List, Optional, Literal, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import math
import requests

app = FastAPI(title="Ads Studio API", version="1.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Schemas ======
class SocialAccount(BaseModel):
    platform: Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"]
    page_name: Optional[str] = None
    access_token: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str = Field(..., description="Campaign name")
    objective: Literal[
        "traffic", "conversions", "engagement", "lead_generation", "reach"
    ] = "traffic"
    headline: str
    primary_text: str
    media_url: Optional[str] = Field(None, description="Image or video URL")
    call_to_action: Literal[
        "shop_now", "learn_more", "sign_up", "contact_us", "download"
    ] = "learn_more"
    destination_url: Optional[str] = None
    daily_budget: float = Field(..., ge=0.7)
    total_budget: Optional[float] = Field(None, ge=0)
    duration_days: Optional[int] = Field(7, ge=1, description="Duration in days")
    currency: Optional[str] = Field("USD", description="Three-letter currency code like USD, NGN")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    audience_location: Optional[str] = None
    audience_age_min: Optional[int] = Field(18, ge=13, le=65)
    audience_age_max: Optional[int] = Field(45, ge=13, le=100)
    audience_interests: Optional[List[str]] = []
    platforms: List[Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"]]
    social_accounts: Optional[List[SocialAccount]] = []

class Campaign(CampaignCreate):
    id: str
    status: Literal["draft", "scheduled", "published", "failed"] = "draft"
    created_at: datetime
    updated_at: datetime

class PublishRequest(BaseModel):
    campaign_id: Optional[str] = None
    campaign: Optional[CampaignCreate] = None

class PublishResult(BaseModel):
    platform: str
    page_name: Optional[str]
    status: Literal["success", "error"]
    message: str

class PublishResponse(BaseModel):
    campaign_id: Optional[str]
    results: List[PublishResult]
    summary: str

# Social token/account schemas
class AccountTokenCreate(BaseModel):
    platform: Literal["facebook", "instagram", "whatsapp", "twitter", "linkedin", "tiktok"]
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    access_token: str
    expires_at: Optional[datetime] = None
    owner_id: Optional[str] = None  # your app's user id if available

class AccountToken(BaseModel):
    id: str
    platform: Literal["facebook", "instagram", "whatsapp", "twitter", "linkedin", "tiktok"]
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    access_token: str
    expires_at: Optional[datetime] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ====== AI Content Writing ======
class AIGenerateRequest(BaseModel):
    brief: str = Field(..., description="Describe the product/offer and any key points")
    platform: Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"] = "facebook"
    tone: Literal["friendly", "professional", "playful", "urgent", "inspirational"] = "friendly"
    brand: Optional[str] = None
    call_to_action: Optional[str] = None
    keywords: Optional[List[str]] = []

class AIVariation(BaseModel):
    headline: str
    primary_text: str
    hashtags: List[str] = []

class AIGenerateResponse(BaseModel):
    platform: str
    tone: str
    brand: Optional[str]
    variations: List[AIVariation]

# ====== AI Image Generation ======
class AIImageRequest(BaseModel):
    prompt: str = Field(..., description="Describe the image you want")
    style: Optional[Literal["photo", "3d", "illustration", "neon", "minimal"]] = "photo"
    width: Optional[int] = Field(1024, ge=256, le=2048)
    height: Optional[int] = Field(1024, ge=256, le=2048)

class AIImageResponse(BaseModel):
    image_url: str
    provider: str = "pollinations"

# ====== Post creation (simple social posts separate from campaigns) ======
class PostCreate(BaseModel):
    platform: Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"]
    content: str
    media_url: Optional[str] = None
    hashtags: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None

class Post(BaseModel):
    id: str
    platform: Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"]
    content: str
    media_url: Optional[str] = None
    hashtags: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None
    status: Literal["draft", "scheduled", "queued", "published", "failed"] = "draft"
    created_at: datetime
    updated_at: datetime

# ====== Comments & Chat ======
class CommentCreate(BaseModel):
    text: str
    author: Optional[str] = None

class Comment(BaseModel):
    id: str
    post_id: str
    text: str
    author: Optional[str] = None
    created_at: datetime

class ChatMessageCreate(BaseModel):
    message: str
    author: Optional[str] = None

class ChatMessage(BaseModel):
    id: str
    post_id: str
    message: str
    author: Optional[str] = None
    created_at: datetime

# ====== Analytics/Insights ======
class CampaignAnalytics(BaseModel):
    campaign_id: str
    predicted_reach: int
    predicted_clicks: int
    predicted_ctr: float
    predicted_cpl: float
    predicted_leads_low: int
    predicted_leads_high: int
    risk_score: float
    suggestions: List[str]
    share_urls: Optional[Dict[str, str]] = None

# ====== Top Post (for new campaigns) ======
class TopPost(BaseModel):
    id: str
    campaign_id: str
    title: str
    summary: str
    media_url: Optional[str] = None
    destination_url: Optional[str] = None
    platforms: List[str] = []
    created_at: datetime

# ====== Database helpers ======
from database import db, create_document, get_documents, get_document_by_id, update_document  # type: ignore

# ====== Routes ======
@app.get("/")
def read_root():
    return {"message": "Ads Studio Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# ===================== Campaigns =====================
@app.post("/api/campaigns", response_model=Campaign)
def create_campaign(payload: CampaignCreate):
    data = payload.model_dump()
    data["status"] = "draft"
    new_id = create_document("campaign", data)
    now = datetime.now(timezone.utc)

    # Create a Top Post entry visible to all social accounts (aggregated page)
    top_data = {
        "campaign_id": new_id,
        "title": payload.headline or payload.name,
        "summary": payload.primary_text[:240],
        "media_url": payload.media_url,
        "destination_url": payload.destination_url,
        "platforms": payload.platforms,
        "created_at": now,
    }
    try:
        create_document("toppost", top_data)
    except Exception:
        pass

    return Campaign(id=new_id, created_at=now, updated_at=now, **payload.model_dump(), status="draft")

@app.get("/api/campaigns")
def list_campaigns(limit: int = 20):
    docs = get_documents("campaign", {}, limit)
    # Normalize ids and dates to strings
    items = []
    for d in docs:
        _id = str(d.get("_id"))
        created_at = d.get("created_at") or datetime.now(timezone.utc)
        updated_at = d.get("updated_at") or created_at
        status = d.get("status", "draft")
        # map back to Campaign
        items.append(
            {
                "id": _id,
                "name": d.get("name"),
                "objective": d.get("objective"),
                "headline": d.get("headline"),
                "primary_text": d.get("primary_text"),
                "media_url": d.get("media_url"),
                "call_to_action": d.get("call_to_action"),
                "destination_url": d.get("destination_url"),
                "daily_budget": d.get("daily_budget"),
                "total_budget": d.get("total_budget"),
                "duration_days": d.get("duration_days", 7),
                "currency": d.get("currency", "USD"),
                "start_date": created_at,
                "end_date": d.get("end_date"),
                "audience_location": d.get("audience_location"),
                "audience_age_min": d.get("audience_age_min"),
                "audience_age_max": d.get("audience_age_max"),
                "audience_interests": d.get("audience_interests", []),
                "platforms": d.get("platforms", []),
                "social_accounts": d.get("social_accounts", []),
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return {"items": items}

# ===================== Accounts/Tokens =====================
@app.get("/api/accounts", response_model=List[AccountToken])
def list_accounts():
    docs = get_documents("token", {})
    items: List[AccountToken] = []
    for d in docs:
        items.append(
            AccountToken(
                id=str(d.get("_id")),
                platform=d.get("platform"),
                page_id=d.get("page_id"),
                page_name=d.get("page_name"),
                access_token=d.get("access_token"),
                expires_at=d.get("expires_at"),
                owner_id=d.get("owner_id"),
                created_at=d.get("created_at"),
                updated_at=d.get("updated_at"),
            )
        )
    return items

@app.post("/api/accounts", response_model=AccountToken)
def upsert_account(body: AccountTokenCreate):
    from bson import ObjectId
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    key_filter = {"platform": body.platform}
    if body.page_id:
        key_filter["page_id"] = body.page_id
    elif body.page_name:
        key_filter["page_name"] = body.page_name
    existing = db["token"].find_one(key_filter)

    data = body.model_dump()
    data["updated_at"] = datetime.now(timezone.utc)
    if existing:
        db["token"].update_one({"_id": existing["_id"]}, {"$set": data})
        saved = db["token"].find_one({"_id": existing["_id"]})
        _id = str(existing["_id"])
        created_at = existing.get("created_at")
    else:
        data["created_at"] = datetime.now(timezone.utc)
        _id = create_document("token", data)
        saved = db["token"].find_one({"_id": ObjectId(_id)})
        created_at = saved.get("created_at") if saved else datetime.now(timezone.utc)

    return AccountToken(id=_id, created_at=created_at, updated_at=data["updated_at"], platform=body.platform, page_id=body.page_id, page_name=body.page_name, access_token=body.access_token, expires_at=body.expires_at, owner_id=body.owner_id)

@app.delete("/api/accounts/{token_id}")
def delete_account(token_id: str):
    from bson import ObjectId
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["token"].delete_one({"_id": ObjectId(token_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "deleted"}

# ===================== OAuth (Meta / WhatsApp scaffolding) =====================
@app.get("/auth/meta/url")
def get_meta_oauth_url(state: Optional[str] = None):
    app_id = os.getenv("META_APP_ID")
    redirect_uri = os.getenv("META_REDIRECT_URI")
    if not app_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="META_APP_ID or META_REDIRECT_URI not configured")
    scope = "pages_manage_metadata,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish,whatsapp_business_messaging,whatsapp_business_management"
    s = state or "state"
    url = (
        "https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={app_id}&redirect_uri={redirect_uri}&state={s}&scope={scope}"
    )
    return {"url": url}

class MetaCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None

@app.post("/auth/meta/callback")
def meta_oauth_callback(body: MetaCallbackRequest):
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    redirect_uri = os.getenv("META_REDIRECT_URI")
    if not app_id or not app_secret or not redirect_uri:
        raise HTTPException(status_code=500, detail="Meta app env vars not configured")

    # Exchange code for user access token
    token_url = "https://graph.facebook.com/v18.0/oauth_access_token"
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": body.code,
    }
    r = requests.get(token_url, params=params, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {r.text}")
    token_payload = r.json()
    user_access_token = token_payload.get("access_token")

    return {"user_access_token": user_access_token}

# ===================== AI Content Generation =====================

def _gen_hashtags(keywords: List[str], platform: str) -> List[str]:
    base = [k.replace(" ", "") for k in (keywords or [])][:5]
    if platform in ("instagram", "tiktok"):
        base = [f"#{b}" for b in base]
    else:
        base = [f"#{b}" for b in base[:3]]
    generic = ["#NexusAds", "#AdTips", "#Marketing"]
    out = base + generic
    seen = set()
    uniq = []
    for h in out:
        if h.lower() not in seen:
            uniq.append(h)
            seen.add(h.lower())
        if len(uniq) >= 8:
            break
    return uniq

@app.post("/api/ai/generate", response_model=AIGenerateResponse)
def ai_generate(body: AIGenerateRequest):
    tone_prefix = {
        "friendly": ["Hey there!", "Great news ✨"],
        "professional": ["Introducing", "We are pleased to announce"],
        "playful": ["Psst…", "Ready to level up?"],
        "urgent": ["Limited time!", "Don’t miss out"],
        "inspirational": ["Imagine this", "Turn your vision into reality"],
    }[body.tone]

    emoji = {
        "facebook": "📣",
        "instagram": "✨",
        "twitter": "🚀",
        "linkedin": "💼",
        "tiktok": "🔥",
    }[body.platform]

    brand = f"{body.brand} — " if body.brand else ""
    cta = body.call_to_action or "Learn more"
    hashtags = _gen_hashtags(body.keywords or [], body.platform)

    base_text = (
        f"{tone_prefix[0]} {brand}{body.brief.strip()} {emoji}\n\n"
        f"{tone_prefix[1]} {cta}."
    )

    variations = [
        AIVariation(
            headline=f"{emoji} {brand} {cta}",
            primary_text=base_text,
            hashtags=hashtags,
        ),
        AIVariation(
            headline=f"{emoji} {brand} {body.brief[:60]}…",
            primary_text=f"{tone_prefix[1]} {body.brief.strip()} — {cta}!",
            hashtags=hashtags,
        ),
        AIVariation(
            headline=f"{emoji} {brand} New: {cta}",
            primary_text=f"{tone_prefix[0]} {body.brief.strip()}\n\n{cta} today.",
            hashtags=hashtags,
        ),
    ]

    return AIGenerateResponse(platform=body.platform, tone=body.tone, brand=body.brand, variations=variations)

# ===================== AI Image Generation Route =====================
@app.post("/api/ai/image", response_model=AIImageResponse)
def ai_image(body: AIImageRequest):
    style_hint = {
        "photo": "high quality photo",
        "3d": "3d render",
        "illustration": "flat illustration",
        "neon": "neon cyberpunk",
        "minimal": "minimal clean",
    }.get(body.style or "photo", "high quality photo")

    prompt = f"{style_hint}, {body.prompt.strip()}"
    from urllib.parse import quote
    pw = max(256, min(2048, body.width or 1024))
    ph = max(256, min(2048, body.height or 1024))
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width={pw}&height={ph}&n=1"
    return AIImageResponse(image_url=url)

# ===================== Simple Posts =====================
@app.get("/api/posts")
def list_posts(limit: int = 20):
    docs = get_documents("post", {}, limit)
    items = []
    for d in docs:
        items.append(
            {
                "id": str(d.get("_id")),
                "platform": d.get("platform"),
                "content": d.get("content"),
                "media_url": d.get("media_url"),
                "hashtags": d.get("hashtags", []),
                "scheduled_at": d.get("scheduled_at"),
                "status": d.get("status", "draft"),
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
            }
        )
    return {"items": items}

@app.post("/api/posts", response_model=Post)
def create_post(body: PostCreate):
    data = body.model_dump()
    now = datetime.now(timezone.utc)
    data["created_at"] = now
    data["updated_at"] = now
    data["status"] = "scheduled" if body.scheduled_at else "queued"
    new_id = create_document("post", data)
    return Post(id=new_id, created_at=now, updated_at=now, status=data["status"], **body.model_dump())

# ===== Comments for Posts =====
@app.get("/api/posts/{post_id}/comments", response_model=List[Comment])
def get_post_comments(post_id: str):
    docs = get_documents("comment", {"post_id": post_id})
    items: List[Comment] = []
    for d in docs:
        items.append(
            Comment(
                id=str(d.get("_id")),
                post_id=d.get("post_id"),
                text=d.get("text"),
                author=d.get("author"),
                created_at=d.get("created_at"),
            )
        )
    return items

@app.post("/api/posts/{post_id}/comments", response_model=Comment)
def add_post_comment(post_id: str, body: CommentCreate):
    now = datetime.now(timezone.utc)
    data = {"post_id": post_id, "text": body.text, "author": body.author, "created_at": now, "updated_at": now}
    comment_id = create_document("comment", data)
    return Comment(id=comment_id, post_id=post_id, text=body.text, author=body.author, created_at=now)

# ===== Chat for Posts =====
@app.get("/api/posts/{post_id}/chat", response_model=List[ChatMessage])
def get_post_chat(post_id: str):
    docs = get_documents("chat", {"post_id": post_id})
    items: List[ChatMessage] = []
    for d in docs:
        items.append(
            ChatMessage(
                id=str(d.get("_id")),
                post_id=d.get("post_id"),
                message=d.get("message"),
                author=d.get("author"),
                created_at=d.get("created_at"),
            )
        )
    return items

@app.post("/api/posts/{post_id}/chat", response_model=ChatMessage)
def add_post_chat(post_id: str, body: ChatMessageCreate):
    now = datetime.now(timezone.utc)
    data = {"post_id": post_id, "message": body.message, "author": body.author, "created_at": now, "updated_at": now}
    chat_id = create_document("chat", data)
    return ChatMessage(id=chat_id, post_id=post_id, message=body.message, author=body.author, created_at=now)

# ===== Top Posts (aggregated page visible to all social accounts) =====
@app.get("/api/top-posts")
def get_top_posts(limit: int = 20):
    docs = get_documents("toppost", {}, limit)
    items = []
    for d in docs:
        items.append(
            {
                "id": str(d.get("_id")),
                "campaign_id": d.get("campaign_id"),
                "title": d.get("title"),
                "summary": d.get("summary"),
                "media_url": d.get("media_url"),
                "destination_url": d.get("destination_url"),
                "platforms": d.get("platforms", []),
                "created_at": d.get("created_at"),
            }
        )
    return {"items": items}

# ===================== Publish =====================
@app.post("/api/publish", response_model=PublishResponse)
def publish_campaign(body: PublishRequest):
    if not body.campaign and not body.campaign_id:
        raise HTTPException(status_code=400, detail="Provide campaign or campaign_id")

    campaign_payload: CampaignCreate
    if body.campaign:
        campaign_payload = body.campaign
    else:
        docs = get_documents("campaign", {})
        found = next((d for d in docs if str(d.get("_id")) == body.campaign_id), None)
        if not found:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign_payload = CampaignCreate(**{k: found.get(k) for k in CampaignCreate.model_fields.keys()})

    results: List[PublishResult] = []
    accounts = (campaign_payload.social_accounts or [])
    accounts = accounts[:5]

    if db is not None and accounts:
        enriched = []
        for acc in accounts:
            if acc.access_token:
                enriched.append(acc)
                continue
            q = {"platform": acc.platform}
            if acc.page_name:
                q["page_name"] = acc.page_name
            doc = db["token"].find_one(q)
            if doc:
                enriched.append(SocialAccount(platform=acc.platform, page_name=doc.get("page_name"), access_token=doc.get("access_token")))
            else:
                enriched.append(acc)
        accounts = enriched

    for acc in accounts:
        if not acc.access_token:
            results.append(
                PublishResult(
                    platform=acc.platform,
                    page_name=acc.page_name,
                    status="error",
                    message="Missing access token for this page",
                )
            )
            continue
        results.append(
            PublishResult(
                platform=acc.platform,
                page_name=acc.page_name,
                status="success",
                message="Queued for publish",
            )
        )

    log = {
        "type": "publish",
        "results": [r.model_dump() for r in results],
        "created_at": datetime.now(timezone.utc),
    }
    create_document("log", log)

    success_count = sum(1 for r in results if r.status == "success")
    summary = f"Prepared {success_count}/{len(results)} posts for publishing"

    return PublishResponse(campaign_id=body.campaign_id, results=results, summary=summary)

# ===================== AI Analytics & Actions =====================

def _calc_predictions(camp: Dict[str, Any]) -> Dict[str, Any]:
    daily = float(camp.get("daily_budget") or 0)
    days = int(camp.get("duration_days") or 7)
    total = float(camp.get("total_budget") or (daily * days))
    reach = int(800 * daily * math.log(days + 1, 2) + 1000)
    clicks = int(reach * 0.02 + daily * 15)
    ctr = round((clicks / max(1, reach)) * 100, 2)
    cpl = round(max(0.2, 1.5 - (daily / 20.0)), 2)
    leads_low = int((total / max(0.01, cpl)) * 0.6)
    leads_high = int((total / max(0.01, cpl)) * 1.1)

    interests = camp.get("audience_interests") or []
    age_min = int(camp.get("audience_age_min") or 18)
    age_max = int(camp.get("audience_age_max") or 45)
    risk = 0.0
    if len(interests) < 2:
        risk += 0.2
    if age_max - age_min < 10:
        risk += 0.2
    if daily < 1:
        risk += 0.3
    risk = round(min(1.0, risk), 2)

    suggestions = []
    if len(interests) < 3:
        suggestions.append("Add 3–5 interest clusters to broaden discovery.")
    if ctr < 1.5:
        suggestions.append("Test 2 more headlines to lift CTR above 1.5%.")
    if cpl > 1.0:
        suggestions.append("Consider optimizing the landing page to improve conversion cost.")
    if days < 5:
        suggestions.append("Increase duration to stabilize delivery and learning phase.")

    return {
        "predicted_reach": reach,
        "predicted_clicks": clicks,
        "predicted_ctr": ctr,
        "predicted_cpl": cpl,
        "predicted_leads_low": leads_low,
        "predicted_leads_high": leads_high,
        "risk_score": risk,
        "suggestions": suggestions,
    }

@app.get("/api/campaigns/{campaign_id}/analytics", response_model=CampaignAnalytics)
def campaign_analytics(campaign_id: str):
    doc = get_document_by_id("campaign", campaign_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")
    preds = _calc_predictions(doc)
    share_urls = _build_share_urls(doc)
    return CampaignAnalytics(campaign_id=campaign_id, share_urls=share_urls, **preds)

@app.post("/api/campaigns/{campaign_id}/boost")
def boost_campaign(campaign_id: str):
    if not get_document_by_id("campaign", campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    update_document("campaign", campaign_id, {"boosts": int(datetime.now().timestamp())})
    create_document("log", {"type": "boost", "campaign_id": campaign_id, "created_at": datetime.now(timezone.utc)})
    return {"status": "ok", "message": "Boost scheduled — budget concentration and frequency cap adjustments queued."}

@app.post("/api/campaigns/{campaign_id}/viral")
def viral_push(campaign_id: str):
    if not get_document_by_id("campaign", campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    update_document("campaign", campaign_id, {"viral_pushes": int(datetime.now().timestamp())})
    create_document("log", {"type": "viral", "campaign_id": campaign_id, "created_at": datetime.now(timezone.utc)})
    return {"status": "ok", "message": "Viral push initiated — top creatives will be re-promoted across platforms."}

# Social share links

def _build_share_urls(camp: Dict[str, Any]) -> Dict[str, str]:
    from urllib.parse import quote_plus
    url = camp.get("destination_url") or "https://nexus-ads.app"
    text = camp.get("headline") or camp.get("primary_text") or "Check this out"
    share = {
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={quote_plus(url)}",
        "twitter": f"https://twitter.com/intent/tweet?text={quote_plus(text)}&url={quote_plus(url)}",
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={quote_plus(url)}",
        "whatsapp": f"https://api.whatsapp.com/send?text={quote_plus(text + ' ' + url)}",
        "telegram": f"https://t.me/share/url?url={quote_plus(url)}&text={quote_plus(text)}",
    }
    return share

@app.get("/api/campaigns/{campaign_id}/share")
def share_links(campaign_id: str):
    doc = get_document_by_id("campaign", campaign_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"campaign_id": campaign_id, "share_urls": _build_share_urls(doc)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
