from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Subscription:
    id: int
    user_id: int
    stripe_subscription_id: str
    plan: str
    status: str  # 'active', 'canceled', 'past_due', etc.
    start_date: datetime
    end_date: Optional[datetime] = None
