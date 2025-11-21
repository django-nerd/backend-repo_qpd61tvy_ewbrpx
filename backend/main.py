import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents, get_document_by_id, update_document, delete_document
from schemas import (
    Campaign, CampaignOut, PublishRequest,
    AccountToken, AccountTokenOut, MetaCallback,
)

APP_VERSION = "1.1.0"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Ads Studio API", version=APP_VERSION)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Collections
COLL_CAMPAIGN = "campaign"
COLL_ACCOUNT = "accounttoken"


@app.get("/", tags=["root"])
def root():
    return {"ok": True, "service": "ads-studio", "version": APP_VERSION}


@app.get("/test", tags=["health"])
def test_db():
    try:
        db.list_collection_names()
        return {"ok": True, "db": "connected"}
    except Exception as e:
        logger.exception("DB connection failed")
        raise HTTPException(status_code=500, detail=str(e))


# Campaigns
@app.post("/api/campaigns", response_model=CampaignOut)
def create_campaign(payload: Campaign):
    created = create_document(COLL_CAMPAIGN, payload.model_dump(exclude_none=True))
    return CampaignOut(**created)


@app.get("/api/campaigns", response_model=List[CampaignOut])
def list_campaigns():
    docs = get_documents(COLL_CAMPAIGN, {})
    return [CampaignOut(**d) for d in docs]


# Accounts
@app.get("/api/accounts", response_model=List[AccountTokenOut])
def list_accounts():
    docs = get_documents(COLL_ACCOUNT, {})
    return [AccountTokenOut(**d) for d in docs]


@app.post("/api/accounts", response_model=AccountTokenOut)
def upsert_account(payload: AccountToken):
    # Upsert by platform + page_id (or platform-only)
    filt: Dict[str, Any] = {"platform": payload.platform}
    if payload.page_id:
        filt["page_id"] = payload.page_id

    existing = db[COLL_ACCOUNT].find_one(filt)
    data = payload.model_dump(exclude_none=True)
    now = datetime.utcnow()

    if existing:
        db[COLL_ACCOUNT].update_one({"_id": existing["_id"]}, {"$set": {**data, "updated_at": now}})
        updated = db[COLL_ACCOUNT].find_one({"_id": existing["_id"]})
        updated["id"] = str(updated.pop("_id"))
        return AccountTokenOut(**updated)
    else:
        created = create_document(COLL_ACCOUNT, data)
        return AccountTokenOut(**created)


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: str):
    ok = delete_document(COLL_ACCOUNT, account_id)
    return {"deleted": ok}


# Publish simulation
@app.post("/api/publish")
def publish_campaign(payload: PublishRequest):
    # Fetch campaign if id provided
    campaign: Optional[Dict[str, Any]] = None
    if payload.campaign_id:
        campaign = get_document_by_id(COLL_CAMPAIGN, payload.campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

    social_accounts = payload.social_accounts or campaign.get("social_accounts", []) if campaign else []
    if not social_accounts:
        raise HTTPException(status_code=400, detail="No social accounts provided")

    results = []
    for acc in social_accounts[:5]:
        # acc can be page_id or a composite like platform:page_id
        platform, page_id = (acc.split(":", 1) + [None])[:2]
        token_doc = None
        # Match by page_id if provided else by platform
        if page_id:
            token_doc = db[COLL_ACCOUNT].find_one({"platform": platform, "page_id": page_id})
        if not token_doc:
            token_doc = db[COLL_ACCOUNT].find_one({"platform": platform})
        if token_doc:
            token = token_doc.get("access_token")
            page_name = token_doc.get("page_name")
            results.append({
                "platform": platform,
                "page_id": page_id or token_doc.get("page_id"),
                "page_name": page_name,
                "status": "queued",
                "detail": "Will publish using stored token",
            })
        else:
            results.append({
                "platform": platform,
                "page_id": page_id,
                "status": "error",
                "detail": "No token found for platform/page",
            })

    return {"ok": True, "results": results}


# Meta OAuth
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI")


def _ensure_meta_env():
    if not META_APP_ID or not META_APP_SECRET or not META_REDIRECT_URI:
        raise HTTPException(status_code=400, detail="Meta OAuth is not configured on server")


@app.get("/auth/meta/url")
def meta_oauth_url():
    _ensure_meta_env()
    scope = "pages_show_list,instagram_basic,pages_read_engagement,pages_manage_posts,business_management"
    auth_url = (
        "https://www.facebook.com/v18.0/dialog/oauth?"
        f"client_id={META_APP_ID}&redirect_uri={META_REDIRECT_URI}?meta_oauth=1&scope={scope}&response_type=code&state=xyz"
    )
    return {"url": auth_url}


@app.post("/auth/meta/callback")
def meta_oauth_callback(payload: MetaCallback):
    _ensure_meta_env()
    code = payload.code
    # Exchange code for user access token
    token_url = (
        "https://graph.facebook.com/v18.0/oauth/access_token?"
        f"client_id={META_APP_ID}&redirect_uri={META_REDIRECT_URI}?meta_oauth=1&client_secret={META_APP_SECRET}&code={code}"
    )
    try:
        r = requests.get(token_url, timeout=15)
        data = r.json()
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=str(data))
        user_access_token = data.get("access_token")
        if not user_access_token:
            raise HTTPException(status_code=400, detail="No access token in response")
        # Store or update a generic meta token entry for convenience
        upsert = AccountToken(platform="facebook", access_token=user_access_token)
        doc = upsert.model_dump(exclude_none=True)
        # Upsert by platform only
        existing = db[COLL_ACCOUNT].find_one({"platform": "facebook", "page_id": {"$exists": False}})
        if existing:
            db[COLL_ACCOUNT].update_one({"_id": existing["_id"]}, {"$set": {**doc, "updated_at": datetime.utcnow()}})
        else:
            create_document(COLL_ACCOUNT, doc)
        return {"ok": True, "token_type": "user", "stored": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Meta callback error")
        raise HTTPException(status_code=500, detail=str(e))
