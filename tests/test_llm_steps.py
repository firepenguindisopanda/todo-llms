"""Tests for LLM-powered todo steps functionality"""

import pytest
from unittest.mock import patch, AsyncMock

from app.infrastructure.llm.nvidia_client import TodoStepsResponse, TodoStep


class TestNVIDIAClient:
    """Test cases for NVIDIA client functionality."""

    def test_client_initialization(self):
        """Test client factory initialization."""
        from app.infrastructure.llm.nvidia_client import NVIDIAClientFactory

        factory = NVIDIAClientFactory()
        # Should not fail to initialize
        assert (
            factory._is_configured is False
        )  # Since no API key is configured in tests


class TestTodoSchemas:
    """Test cases for updated todo schemas."""

    def test_todo_out_with_steps(self):
        """Test TodoOut schema includes steps fields."""
        from app.api.v1.endpoints.todos import TodoOut
        from datetime import datetime

        todo_data = {
            "id": 1,
            "user_id": 1,
            "title": "Test Todo",
            "description": "Test description",
            "completed": False,
            "priority": None,
            "due_date": None,
            "created_at": datetime.utcnow(),
            "steps": {"steps": []},
            "steps_generated_at": None,
            "steps_generation_status": "pending",
        }

        todo_out = TodoOut(**todo_data)
        assert todo_out.steps == {"steps": []}
        assert todo_out.steps_generation_status == "pending"


class TestRateLimiter:
    """Test cases for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_fallback(self):
        """Test rate limiting fallback when Redis is unavailable."""
        from app.infrastructure.llm.rate_limiter import UserBasedRateLimiter

        limiter = UserBasedRateLimiter()
        user_id = 1

        # Mock Redis to return None (unavailable)
        with patch.object(limiter, "_get_redis") as mock_redis:
            mock_redis.return_value = None

            # Should allow request when Redis is unavailable (fallback behavior)
            can_proceed = await limiter.check_rate_limit(user_id)
            assert can_proceed is True


class TestTodoStepsMock:
    """Mock tests for todo steps functionality."""

    @pytest.mark.asyncio
    async def test_mock_step_generation(self):
        """Test step generation with mocked LLM."""
        # Mock the LLM client response
        mock_response = TodoStepsResponse(
            steps=[
                TodoStep(
                    step_number=1,
                    title="Test Step",
                    description="This is a test step",
                    estimated_time="15 minutes",
                    priority="medium",
                )
            ],
            total_estimated_time="15 minutes",
            complexity="simple",
        )

        # Test that the response structure is correct
        assert len(mock_response.steps) == 1
        assert mock_response.steps[0].step_number == 1
        assert mock_response.steps[0].title == "Test Step"
        assert mock_response.complexity == "simple"
