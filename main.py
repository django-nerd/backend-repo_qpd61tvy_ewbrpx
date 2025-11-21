import os
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import requests

app = FastAPI(title="Ads Studio API", version="1.1.0")

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
    daily_budget: float = Field(..., ge=1)
    total_budget: Optional[float] = Field(None, ge=1)
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

class AccountToken(AccountTokenCreate):
    id: str
    created_at: datetime
    updated_at: datetime

# ====== Database helpers ======
from database import db, create_document, get_documents, get_document_by_id  # type: ignore

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
    # naive upsert by platform+page_id or page_name
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

    return AccountToken(id=_id, created_at=created_at, updated_at=data["updated_at"], **body.model_dump())

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
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
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

    # Example: return token. In production, fetch pages and store page tokens via /me/accounts
    return {"user_access_token": user_access_token}

# ===================== Publish =====================
@app.post("/api/publish", response_model=PublishResponse)
def publish_campaign(body: PublishRequest):
    if not body.campaign and not body.campaign_id:
        raise HTTPException(status_code=400, detail="Provide campaign or campaign_id")

    campaign_payload: CampaignCreate
    if body.campaign:
        campaign_payload = body.campaign
    else:
        # fetch from db
        docs = get_documents("campaign", {})
        found = next((d for d in docs if str(d.get("_id")) == body.campaign_id), None)
        if not found:
            raise HTTPException(status_code=404, detail="Campaign not found")
        # reconstruct model
        campaign_payload = CampaignCreate(**{k: found.get(k) for k in CampaignCreate.model_fields.keys()})

    results: List[PublishResult] = []
    accounts = (campaign_payload.social_accounts or [])

    # Enforce max 5 social media pages as requested
    accounts = accounts[:5]

    # Try enrich accounts with saved tokens if not provided
    if db is not None and accounts:
        enriched = []
        for acc in accounts:
            if acc.access_token:
                enriched.append(acc)
                continue
            # Try lookup by platform + page_name
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
        # Simulate or call real APIs depending on platform
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
        # Placeholder for real integration calls
        results.append(
            PublishResult(
                platform=acc.platform,
                page_name=acc.page_name,
                status="success",
                message="Queued for publish",
            )
        )

    # Store a publish log
    log = {
        "type": "publish",
        "results": [r.model_dump() for r in results],
        "created_at": datetime.now(timezone.utc),
    }
    create_document("log", log)

    success_count = sum(1 for r in results if r.status == "success")
    summary = f"Prepared {success_count}/{len(results)} posts for publishing"

    return PublishResponse(campaign_id=body.campaign_id, results=results, summary=summary)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
