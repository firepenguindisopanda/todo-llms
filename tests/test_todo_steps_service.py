
import pytest
from unittest.mock import AsyncMock
from app.infrastructure.llm.todo_steps_service import TodoStepsService
from app.infrastructure.llm.nvidia_client import TodoStepsResponse, TodoStep

class DummyDB:
    async def execute(self, *a, **k): return None
    async def commit(self): pass
    async def refresh(self, *a, **k): pass
    async def get(self, model, id):
        class DummyTodo:
            id = 1
            user_id = 1
            title = "Test"
            description = "desc"
            steps_generation_status = "pending"
        return DummyTodo()

@pytest.mark.asyncio
async def test_generate_and_store_steps_failure(monkeypatch):
    db = DummyDB()
    service = TodoStepsService(db)
    # Patch LLM client to simulate failure
    monkeypatch.setattr(
        "app.infrastructure.llm.nvidia_client.nvidia_client_factory.generate_todo_steps",
        AsyncMock(return_value=None)
    )
    # Patch update methods to no-op
    monkeypatch.setattr(service, "_update_generation_status", AsyncMock())
    monkeypatch.setattr(service, "_store_steps", AsyncMock())
    monkeypatch.setattr(service, "_get_redis", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_get_todo_for_user", AsyncMock(return_value=await db.get(None, 1)))
    result = await service.generate_and_store_steps(todo_id=1, user_id=1)
    assert result is False

@pytest.mark.asyncio
async def test_generate_and_store_steps_success(monkeypatch):
    db = DummyDB()
    service = TodoStepsService(db)
    # Patch LLM client to simulate success
    mock_response = TodoStepsResponse(
        steps=[TodoStep(step_number=1, title="Step 1", description="desc", estimated_time="10m", priority="medium")],
        total_estimated_time="10m",
        complexity="simple"
    )
    monkeypatch.setattr(
        "app.infrastructure.llm.nvidia_client.nvidia_client_factory.generate_todo_steps",
        AsyncMock(return_value=mock_response)
    )
    monkeypatch.setattr(service, "_update_generation_status", AsyncMock())
    monkeypatch.setattr(service, "_store_steps", AsyncMock())
    monkeypatch.setattr(service, "_get_redis", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_get_todo_for_user", AsyncMock(return_value=await db.get(None, 1)))
    result = await service.generate_and_store_steps(todo_id=1, user_id=1)
    assert result is True
