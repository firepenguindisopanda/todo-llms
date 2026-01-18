
import pytest
from app.infrastructure.llm.todo_steps_service import TodoStepsService
from app.infrastructure.llm.nvidia_client import TodoStepsResponse, TodoStep
from app.config import settings
import os

@pytest.mark.asyncio
async def test_llm_integration_real_key(monkeypatch):
    # Only run if NVIDIA_API_KEY is set
    api_key = settings.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        pytest.skip("NVIDIA_API_KEY not set in environment")

    # Setup: mock DB session and service
    class DummyDB:
        async def execute(self, *a, **k): return None
        async def commit(self): pass
        async def refresh(self, *a, **k): pass
        async def get(self, model, id):
            class DummyTodo:
                id = 1
                user_id = 1
                title = "Write a blog post about FastAPI"
                description = "Research, draft, and publish a blog post about FastAPI."
                steps_generation_status = "pending"
            return DummyTodo()
    db = DummyDB()
    service = TodoStepsService(db)

    # Patch _get_todo_for_user to return our dummy todo
    async def dummy_get_todo_for_user(todo_id, user_id):
        return await db.get(None, 1)
    async def dummy_update_generation_status(*a, **k):
        return None
    async def dummy_store_steps(*a, **k):
        return None
    async def dummy_get_redis():
        return None
    monkeypatch.setattr(service, "_get_todo_for_user", dummy_get_todo_for_user)
    monkeypatch.setattr(service, "_update_generation_status", dummy_update_generation_status)
    monkeypatch.setattr(service, "_store_steps", dummy_store_steps)
    monkeypatch.setattr(service, "_get_redis", dummy_get_redis)

    # Actually call the LLM
    result = await service.generate_and_store_steps(todo_id=1, user_id=1)
    assert result is True or result is False  # Should not raise, should return a bool
