"""NVIDIA NIM LLM Client Factory

Follows LangChain best practices for LLM client management and configuration.
Provides centralized NVIDIA NIM client initialization with proper error handling,
rate limiting, and observability.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
except ImportError:
    ChatNVIDIA = None

from app.config import settings
from app.logging_config import logger


# Pydantic model for structured step generation
class TodoStep(BaseModel):
    """Represents a single actionable step for completing a todo."""

    step_number: int = Field(..., description="Sequential order of the step")
    title: str = Field(..., description="Brief title for the step")
    description: str = Field(..., description="Detailed description of what to do")
    estimated_time: Optional[str] = Field(
        None, description="Estimated time to complete (e.g., '15 minutes', '1 hour')"
    )
    priority: str = Field(
        default="medium", description="Priority level: low, medium, high"
    )


class TodoStepsResponse(BaseModel):
    """Structured response containing generated steps for a todo."""

    steps: List[TodoStep] = Field(..., description="List of actionable steps")
    total_estimated_time: Optional[str] = Field(
        None, description="Total estimated time for all steps"
    )
    complexity: str = Field(
        default="medium", description="Overall complexity: simple, medium, complex"
    )


class NVIDIAClientFactory:
    """Factory for creating and configuring NVIDIA NIM LLM clients.

    Implements LangChain best practices for:
    - Centralized configuration management
    - Proper error handling and fallbacks
    - Rate limiting integration
    - Observability and logging
    - Structured output generation
    """

    def __init__(self):
        self._chat_model: Optional[ChatNVIDIA] = None
        self._output_parser = JsonOutputParser(pydantic_object=TodoStepsResponse)
        self._is_configured = False

    def _validate_configuration(self) -> bool:
        """Validate that required NVIDIA NIM configuration is present."""
        if not settings.NVIDIA_API_KEY:
            logger.warning(
                "NVIDIA_API_KEY not configured - LLM features will be disabled"
            )
            return False

        if ChatNVIDIA is None:
            logger.error("langchain-nvidia-ai-endpoints package not installed")
            return False

        return True

    def _get_chat_model(self) -> Optional[ChatNVIDIA]:
        """Initialize and return a ChatNVIDIA instance with proper configuration."""
        if not self._validate_configuration():
            return None

        if self._chat_model is None:
            try:
                model_config = {
                    "model": settings.NVIDIA_MODEL_NAME,
                    "api_key": settings.NVIDIA_API_KEY,
                    "temperature": settings.NVIDIA_TEMPERATURE,
                    "max_completion_tokens": settings.NVIDIA_MAX_COMPLETION_TOKENS,
                    "timeout": settings.NVIDIA_TIMEOUT,
                }

                logger.info(
                    f"Initializing ChatNVIDIA with model: {settings.NVIDIA_MODEL_NAME}"
                )
                self._chat_model = ChatNVIDIA(**model_config)
                self._is_configured = True

            except Exception as exc:
                logger.error(f"Failed to initialize ChatNVIDIA: {exc}")
                return None

        return self._chat_model

    def get_structured_chain(self) -> Optional[Runnable]:
        """Get a chain configured for structured step generation.

        Returns:
            Runnable chain that outputs structured TodoStepsResponse
        """
        chat_model = self._get_chat_model()
        if chat_model is None:
            return None

        try:
            # Configure for structured output
            structured_model = chat_model.with_structured_output(TodoStepsResponse)
            logger.info("Created structured output chain for todo steps generation")
            return structured_model

        except Exception as exc:
            logger.error(f"Failed to create structured chain: {exc}")
            return None

    async def generate_todo_steps(
        self, title: str, description: Optional[str] = None
    ) -> Optional[TodoStepsResponse]:
        """Generate actionable steps for a todo item.

        Args:
            title: Todo title
            description: Optional todo description

        Returns:
            TodoStepsResponse with generated steps, or None if generation fails
        """
        chain = self.get_structured_chain()
        if chain is None:
            return None

        try:
            # Load prompt template
            prompt = self._load_steps_prompt()

            # Format prompt with todo details
            formatted_prompt = prompt.format(
                title=title,
                description=description or "No description provided",
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )

            logger.info(f"Generating steps for todo: {title}")

            # Generate structured response
            response = await chain.ainvoke(formatted_prompt)

            # Validate response structure
            if not isinstance(response, TodoStepsResponse):
                logger.error(f"Unexpected response type: {type(response)}")
                return None

            logger.info(
                f"Successfully generated {len(response.steps)} steps for todo: {title}"
            )
            return response

        except Exception as exc:
            logger.error(f"Failed to generate steps for todo '{title}': {exc}")
            return None

    def _load_steps_prompt(self) -> str:
        """Load the prompt template for todo step generation.

        Returns:
            Formatted prompt string
        """
        # For now, include the prompt inline. In production, this would be loaded
        # from prompts/generate_todo_steps.txt following LangChain best practices.
        return """You are an expert task planner and project manager. Your role is to break down tasks into actionable, sequential steps.

Given a todo item with the following details:
- Title: {title}
- Description: {description}
- Current Date: {current_date}

Generate a comprehensive list of steps to complete this task successfully. Follow these guidelines:

1. Create 3-8 actionable steps depending on task complexity
2. Each step should be specific and measurable
3. Order steps logically (prerequisites first)
4. Provide realistic time estimates
5. Assign appropriate priority levels
6. Focus on practical, executable actions

Format your response as a JSON object with the following structure:
{{
  "steps": [
    {{
      "step_number": 1,
      "title": "Brief action title",
      "description": "Detailed description of what to do",
      "estimated_time": "15 minutes",
      "priority": "high"
    }}
  ],
  "total_estimated_time": "1 hour 30 minutes",
  "complexity": "medium"
}}

Consider the context and make reasonable assumptions about the task. If the description is vague, infer the most likely intent and create steps accordingly."""


# Singleton instance for application-wide use
nvidia_client_factory = NVIDIAClientFactory()
