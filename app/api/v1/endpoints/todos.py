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
from app.logging_config import logger

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
    steps: Optional[dict] = None
    steps_generated_at: Optional[datetime] = None
    steps_generation_status: Optional[str] = None


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
    subscription_status = getattr(current_user, "subscription_status", "free")
    if subscription_status != "active" and todo_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free users can only create up to 10 todos. Please subscribe to add more.",
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

    # Generate AI steps for the todo (background process with separate session)
    try:
        # Check rate limits before generating steps
        from app.infrastructure.llm.rate_limiter import UserBasedRateLimiter

        rate_limiter = UserBasedRateLimiter()

        can_proceed = await rate_limiter.check_rate_limit(current_user.id)
        if can_proceed:
            # Generate steps asynchronously with separate database session
            import asyncio
            from app.infrastructure.database.connection import get_async_session

            async def generate_steps_background():
                try:
                    async for session in get_async_session():
                        from app.infrastructure.llm.todo_steps_service import (
                            TodoStepsService,
                        )

                        steps_service = TodoStepsService(session)
                        await steps_service.generate_and_store_steps(
                            todo.id, current_user.id
                        )
                        await rate_limiter.increment_usage(current_user.id)
                        break  # Only use one session
                except Exception as exc:
                    logger.error(
                        f"Background step generation failed for todo {todo.id}: {exc}"
                    )

            asyncio.create_task(generate_steps_background())
        else:
            logger.warning(
                f"Rate limit exceeded for user {current_user.id} - skipping steps generation"
            )

    except Exception as exc:
        logger.error(f"Failed to trigger steps generation for todo {todo.id}: {exc}")

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
        steps=todo.steps,
        steps_generated_at=todo.steps_generated_at,
        steps_generation_status=todo.steps_generation_status,
    )


@router.get("/{todo_id}", response_model=TodoOut)
async def get_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get a single todo by ID (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(
            TodoModel.id == todo_id, TodoModel.user_id == current_user.id
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
        steps=todo.steps,
        steps_generated_at=todo.steps_generated_at,
        steps_generation_status=todo.steps_generation_status,
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
        select(TodoModel).where(
            TodoModel.id == todo_id, TodoModel.user_id == current_user.id
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

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
        steps=todo.steps,
        steps_generated_at=todo.steps_generated_at,
        steps_generation_status=todo.steps_generation_status,
    )


@router.get("/{todo_id}/details", response_model=TodoOut)
async def get_todo_with_steps(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get a single todo with AI-generated steps (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(
            TodoModel.id == todo_id, TodoModel.user_id == current_user.id
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    return TodoOut(
        id=todo.id,
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        priority=todo.priority,
        due_date=todo.due_date,
        created_at=todo.created_at,
        steps=todo.steps,
        steps_generated_at=todo.steps_generated_at,
        steps_generation_status=todo.steps_generation_status,
    )


@router.get("/{todo_id}/with-steps", response_model=TodoOut)
async def get_todo_with_steps_alias(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Alias endpoint for /{todo_id}/details to maintain backward compatibility."""
    return await get_todo_with_steps(todo_id, db, current_user)


@router.post("/{todo_id}/regenerate-steps", response_model=TodoOut)
async def regenerate_todo_steps(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Regenerate AI steps for a todo (must belong to current user)."""
    # Check rate limits
    from app.infrastructure.llm.rate_limiter import UserBasedRateLimiter

    rate_limiter = UserBasedRateLimiter()

    can_proceed = await rate_limiter.check_rate_limit(current_user.id)
    if not can_proceed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    # Get todo
    result = await db.execute(
        select(TodoModel).where(
            TodoModel.id == todo_id, TodoModel.user_id == current_user.id
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    # Regenerate steps with separate session
    async def regenerate_steps_background():
        try:
            from app.infrastructure.database.connection import get_async_session

            async for session in get_async_session():
                from app.infrastructure.llm.todo_steps_service import TodoStepsService

                steps_service = TodoStepsService(session)
                return await steps_service.regenerate_steps(todo_id, current_user.id)
        except Exception as exc:
            logger.error(
                f"Background step regeneration failed for todo {todo_id}: {exc}"
            )
            return False

    success = await regenerate_steps_background()

    if success:
        # Increment rate limit usage
        await rate_limiter.increment_usage(current_user.id)

        # Refresh todo data
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
            steps=todo.steps,
            steps_generated_at=todo.steps_generated_at,
            steps_generation_status=todo.steps_generation_status,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate steps. Please try again later.",
        )


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Delete a todo (must belong to current user)."""
    result = await db.execute(
        select(TodoModel).where(
            TodoModel.id == todo_id, TodoModel.user_id == current_user.id
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    await db.delete(todo)
    await db.commit()
    return None
