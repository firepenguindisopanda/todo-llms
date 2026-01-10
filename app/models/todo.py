from pydantic import BaseModel

class Todo(BaseModel):
    id: int
    title: str
    description: str | None = None
    completed: bool = False