from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

# Collections: inferred by class name lowercased

class Budget(BaseModel):
    daily: Optional[float] = None
    lifetime: Optional[float] = None
    currency: Optional[str] = "USD"

class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class Audience(BaseModel):
    locations: Optional[List[str]] = None
    genders: Optional[List[str]] = None
    ages: Optional[List[int]] = None
    interests: Optional[List[str]] = None

class Campaign(BaseModel):
    name: str
    objective: Optional[str] = None
    headline: Optional[str] = None
    primary_text: Optional[str] = None
    media_url: Optional[str] = None
    call_to_action: Optional[str] = None
    destination_url: Optional[str] = None
    budgets: Optional[Budget] = None
    dates: Optional[DateRange] = None
    audience: Optional[Audience] = None
    platforms: Optional[List[str]] = None
    social_accounts: Optional[List[str]] = None

class CampaignOut(Campaign):
    id: str

class PublishRequest(BaseModel):
    campaign_id: Optional[str] = None
    social_accounts: Optional[List[str]] = None

class AccountToken(BaseModel):
    platform: str
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    access_token: str
    expires_at: Optional[str] = None
    owner_id: Optional[str] = None

class AccountTokenOut(AccountToken):
    id: str

class MetaCallback(BaseModel):
    code: str
    state: Optional[str] = None
