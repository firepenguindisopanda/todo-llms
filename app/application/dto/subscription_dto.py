from dataclasses import dataclass
from typing import Optional

@dataclass
class SubscriptionDTO:
    user_id: int
    plan: str
    status: str
    stripe_subscription_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@dataclass
class StripeSessionDTO:
    session_id: str
    url: str
