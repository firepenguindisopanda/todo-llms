"""Todo Steps Generation Service

Implements business logic for generating and managing AI-powered todo steps.
Follows LangChain best practices for service layer architecture.
"""

import logging
from typing import Optional, List
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.infrastructure.database.models.todo_model import Todo as TodoModel
from app.infrastructure.llm.nvidia_client import (
    nvidia_client_factory,
    TodoStepsResponse,
    TodoStep,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.logging_config import logger


class TodoStepsService:
    """Service for generating and managing AI-powered todo steps.

    Provides:
    - Steps generation using NVIDIA NIM LLM
    - Caching layer for performance
    - Rate limiting integration
    - Error handling and fallbacks
    - Structured data validation
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_client = None

    async def _get_redis(self):
        """Get Redis client for caching."""
        if self.redis_client is None:
            self.redis_client = get_redis_client()
        return self.redis_client

    async def generate_and_store_steps(self, todo_id: int, user_id: int) -> bool:
        """Generate steps for a todo and store them in database.

        Args:
            todo_id: ID of the todo to generate steps for
            user_id: ID of the user requesting steps (for rate limiting)

        Returns:
            True if steps were generated and stored, False otherwise
        """
        try:
            # Get todo details
            todo = await self._get_todo_for_user(todo_id, user_id)
            if todo is None:
                logger.warning(f"Todo {todo_id} not found for user {user_id}")
                return False

            # Check if steps already generated
            if getattr(todo, "steps_generation_status", None) == "completed":
                logger.info(f"Steps already generated for todo {todo_id}")
                return True

            # Check cache first
            cache_key = f"todo_steps:{todo_id}"
            redis = await self._get_redis()
            if redis:
                try:
                    cached_steps = redis.get(cache_key)
                    if cached_steps:
                        logger.info(f"Using cached steps for todo {todo_id}")
                        await self._update_todo_with_cached_steps(
                            todo_id, json.loads(cached_steps)
                        )
                        return True
                except Exception as exc:
                    logger.warning(f"Cache retrieval failed: {exc}")

            # Mark as generating
            await self._update_generation_status(todo_id, "generating")

            # Generate steps using LLM
            steps_response = await nvidia_client_factory.generate_todo_steps(
                title=str(getattr(todo, "title", "")),
                description=(
                    str(getattr(todo, "description", ""))
                    if getattr(todo, "description", None)
                    else None
                ),
            )

            if steps_response is None:
                logger.error(f"Failed to generate steps for todo {todo_id}")
                await self._update_generation_status(todo_id, "failed")
                return False

            # Store steps in database
            await self._store_steps(todo_id, steps_response)

            # Cache steps for future requests
            if redis:
                try:
                    steps_dict = steps_response.dict()
                    redis.setex(
                        cache_key,
                        3600,  # 1 hour cache
                        json.dumps(steps_dict),
                    )
                    logger.info(f"Cached steps for todo {todo_id}")
                except Exception as exc:
                    logger.warning(f"Cache storage failed: {exc}")

            logger.info(
                f"Successfully generated and stored {len(steps_response.steps)} steps for todo {todo_id}"
            )
            return True

        except Exception as exc:
            logger.error(f"Error generating steps for todo {todo_id}: {exc}")
            await self._update_generation_status(todo_id, "failed")
            return False

    async def get_todo_with_steps(
        self, todo_id: int, user_id: int
    ) -> Optional[TodoModel]:
        """Get todo with its generated steps.

        Args:
            todo_id: ID of the todo
            user_id: ID of the user requesting the todo

        Returns:
            Todo model with steps, or None if not found
        """
        todo = await self._get_todo_for_user(todo_id, user_id)
        if todo is None:
            return None

        # If steps not yet generated, trigger generation in background and return immediately
        if getattr(todo, "steps_generation_status", None) == "pending":
            logger.info(f"Triggering step generation for pending todo {todo_id}")
            # Set status to 'generating' and return immediately
            await self._update_generation_status(todo_id, "generating")

            import asyncio

            async def background_generate():
                try:
                    # Use a separate database session for background task
                    from app.infrastructure.database.connection import get_async_session

                    async for session in get_async_session():
                        background_service = TodoStepsService(session)
                        await background_service.generate_and_store_steps(
                            todo_id, user_id
                        )
                        break  # Only use one session
                except Exception as exc:
                    logger.error(
                        f"Background step generation failed for todo {todo_id}: {exc}"
                    )
                    # Use original session to update status
                    try:
                        await self._update_generation_status(todo_id, "failed")
                    except Exception as status_exc:
                        logger.error(
                            f"Failed to update generation status: {status_exc}"
                        )

            # Save the task to prevent garbage collection and ensure proper cleanup
            self._background_task = asyncio.create_task(background_generate())
            self._background_task.add_done_callback(
                lambda task: None
            )  # Prevent warnings

            # Fetch updated todo (now with status 'generating')
            todo = await self._get_todo_for_user(todo_id, user_id)

        return todo

    async def regenerate_steps(self, todo_id: int, user_id: int) -> bool:
        """Force regeneration of steps for a todo.

        Args:
            todo_id: ID of the todo
            user_id: ID of the user requesting regeneration

        Returns:
            True if regeneration was successful, False otherwise
        """
        try:
            # Clear cache
            redis = await self._get_redis()
            if redis:
                try:
                    cache_key = f"todo_steps:{todo_id}"
                    redis.delete(cache_key)
                    logger.info(f"Cleared cache for todo {todo_id}")
                except Exception as exc:
                    logger.warning(f"Cache clearing failed: {exc}")

            # Reset generation status to trigger regeneration
            await self._update_generation_status(todo_id, "pending")

            # Generate new steps
            return await self.generate_and_store_steps(todo_id, user_id)

        except Exception as exc:
            logger.error(f"Error regenerating steps for todo {todo_id}: {exc}")
            return False

    async def _get_todo_for_user(
        self, todo_id: int, user_id: int
    ) -> Optional[TodoModel]:
        """Get todo that belongs to specific user."""
        result = await self.db.execute(
            select(TodoModel).where(
                TodoModel.id == todo_id, TodoModel.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def _update_generation_status(self, todo_id: int, status: str) -> None:
        """Update the generation status of a todo."""
        from datetime import timezone

        await self.db.execute(
            update(TodoModel)
            .where(TodoModel.id == todo_id)
            .values(
                steps_generation_status=status, updated_at=datetime.now(timezone.utc)
            )
        )
        await self.db.commit()

    async def _store_steps(
        self, todo_id: int, steps_response: TodoStepsResponse
    ) -> None:
        """Store generated steps in the todo."""
        steps_dict = steps_response.dict()

        from datetime import timezone

        await self.db.execute(
            update(TodoModel)
            .where(TodoModel.id == todo_id)
            .values(
                steps=steps_dict,
                steps_generated_at=datetime.now(timezone.utc),
                steps_generation_status="completed",
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()

    async def _update_todo_with_cached_steps(
        self, todo_id: int, steps_data: dict
    ) -> None:
        """Update todo with cached steps data."""
        from datetime import timezone

        await self.db.execute(
            update(TodoModel)
            .where(TodoModel.id == todo_id)
            .values(
                steps=steps_data,
                steps_generated_at=datetime.now(timezone.utc),
                steps_generation_status="completed",
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
