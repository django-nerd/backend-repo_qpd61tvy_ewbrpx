from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Campaign schema to back the database collection
class Campaign(BaseModel):
    name: str
    objective: Literal[
        "traffic", "conversions", "engagement", "lead_generation", "reach"
    ] = "traffic"
    headline: str
    primary_text: str
    media_url: Optional[str] = None
    call_to_action: Literal[
        "shop_now", "learn_more", "sign_up", "contact_us", "download"
    ] = "learn_more"
    destination_url: Optional[str] = None
    daily_budget: float = Field(..., ge=1)
    total_budget: Optional[float] = Field(None, ge=1)
    audience_location: Optional[str] = None
    audience_age_min: Optional[int] = Field(18, ge=13, le=65)
    audience_age_max: Optional[int] = Field(45, ge=13, le=100)
    audience_interests: Optional[List[str]] = []
    platforms: List[Literal["facebook", "instagram", "twitter", "linkedin", "tiktok"]] = []
    social_accounts: Optional[List[dict]] = []
