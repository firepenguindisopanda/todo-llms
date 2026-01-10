from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Todo:
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None
