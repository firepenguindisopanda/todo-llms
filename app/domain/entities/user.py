from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass

class User:
    id: int
    email: str
    password_hash: str
    is_active: bool = True
    is_verified: bool = False
    role: str = "user"
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None
    # Stripe integration fields
    stripe_customer_id: Optional[str] = None
    subscription_status: str = "free"  # 'free', 'active', 'canceled'
    subscription_plan: Optional[str] = None
