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
