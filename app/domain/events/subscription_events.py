from dataclasses import dataclass
from datetime import datetime

@dataclass
class SubscriptionCreatedEvent:
    user_id: int
    subscription_id: int
    plan: str
    timestamp: datetime

@dataclass
class SubscriptionCanceledEvent:
    user_id: int
    subscription_id: int
    plan: str
    timestamp: datetime

@dataclass
class SubscriptionRenewedEvent:
    user_id: int
    subscription_id: int
    plan: str
    timestamp: datetime
