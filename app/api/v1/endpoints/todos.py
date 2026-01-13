from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models.todo_model import Todo as TodoModel
from app.infrastructure.database.models.user_model import User as UserModel

router = APIRouter()


# ---------- Schemas ----------

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None


class TodoOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    completed: bool
    priority: Optional[int]
    due_date: Optional[datetime]
    created_at: datetime


class PaginatedTodos(BaseModel):
    items: List[TodoOut]
    total: int
    page: int
    page_size: int
    pages: int


# ---------- Endpoints ----------

@router.get("/", response_model=PaginatedTodos)
async def list_todos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """List todos for the authenticated user with pagination."""
    # Count total
    count_stmt = select(TodoModel).where(TodoModel.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    all_todos = count_result.scalars().all()
    total = len(all_todos)

    # Paginate
    offset = (page - 1) * page_size
    stmt = (
        select(TodoModel)
        .where(TodoModel.user_id == current_user.id)
        .order_by(TodoModel.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    todos = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total else 1

    return PaginatedTodos(
        items=[
            TodoOut(
                id=t.id,
                user_id=t.user_id,
                title=t.title,
                description=t.description,
                completed=t.completed,
                priority=t.priority,
                due_date=t.due_date,
                created_at=t.created_at,
            )
            for t in todos
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/", status_code=201, response_model=TodoOut)

async def create_todo(
    todo_in: TodoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Create a new todo for the authenticated user, enforcing free/paid limits."""
    # Count current todos for user
    count_stmt = select(TodoModel).where(TodoModel.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    todo_count = len(count_result.scalars().all())

    # Check subscription status (assume 'subscription_status' is available on current_user)
    subscription_status = getattr(current_user, 'subscription_status', 'free')
    if subscription_status != 'active' and todo_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free users can only create up to 10 todos. Please subscribe to add more."
        )

    todo = TodoModel(
        user_id=current_user.id,
        title=todo_in.title,
        description=todo_in.description,
        priority=todo_in.priority,
        due_date=todo_in.due_date,
    )
    db.add(todo)
    await db.flush()
    await db.commit()
    await db.refresh(todo)

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
    )


@router.get("/{todo_id}", response_model=TodoOut)
async def get_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get a single todo by ID (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(TodoModel.id == todo_id, TodoModel.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
    )


@router.put("/{todo_id}", response_model=TodoOut)
async def update_todo(
    todo_id: int,
    todo_in: TodoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Update a todo (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(TodoModel.id == todo_id, TodoModel.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    update_data = todo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(todo, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(todo)

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
    )


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Delete a todo (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(TodoModel.id == todo_id, TodoModel.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    await db.delete(todo)
    await db.commit()
    return None
