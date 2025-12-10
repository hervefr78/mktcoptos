"""
Agent Logger Service - Captures all communication between orchestrator and agents.

This service logs:
- Full system and user prompts
- Input context (topic, audience, previous stage results)
- Raw LLM responses
- Model settings (temperature, token counts)
- Timing information
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from .models import PipelineStepResult

logger = logging.getLogger(__name__)


class AgentLogger:
    """
    Logs agent communication for debugging and review.

    Usage:
        logger = AgentLogger(db, execution_id)

        # Start logging a stage
        logger.start_stage("writer", 4)

        # Log the prompt
        logger.log_prompt(
            system_prompt="You are a content writer...",
            user_prompt="Write a blog post about AI...",
            input_context={"topic": "AI", "outline": {...}}
        )

        # Log the response
        logger.log_response(
            raw_response="Here is the content...",
            parsed_result={"content": "...", "word_count": 1000},
            model="gpt-4o-mini",
            temperature=0.7,
            input_tokens=500,
            output_tokens=1500
        )

        # Complete the stage
        logger.complete_stage(duration_seconds=15)
    """

    def __init__(self, db: Session, execution_id: int):
        self.db = db
        self.execution_id = execution_id
        self._current_step: Optional[PipelineStepResult] = None

    def start_stage(self, stage: str, stage_order: int) -> PipelineStepResult:
        """
        Start logging a new pipeline stage.

        Args:
            stage: Stage identifier (e.g., "writer", "seo_optimizer")
            stage_order: Order in pipeline (1-7)

        Returns:
            The created PipelineStepResult record
        """
        # Check if step already exists (for resume scenarios)
        existing = self.db.query(PipelineStepResult).filter(
            PipelineStepResult.execution_id == self.execution_id,
            PipelineStepResult.stage == stage
        ).first()

        if existing:
            # Update existing step for retry
            existing.status = "running"
            existing.started_at = datetime.utcnow()
            existing.retry_count = (existing.retry_count or 0) + 1
            existing.error_message = None
            self._current_step = existing
        else:
            # Create new step
            self._current_step = PipelineStepResult(
                execution_id=self.execution_id,
                stage=stage,
                stage_order=stage_order,
                status="running",
                started_at=datetime.utcnow()
            )
            self.db.add(self._current_step)

        self.db.commit()
        self.db.refresh(self._current_step)

        logger.info(f"Started logging stage: {stage} (order: {stage_order})")
        return self._current_step

    def log_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        input_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log the prompts sent to the LLM.

        Args:
            system_prompt: Full system prompt
            user_prompt: User message/prompt
            input_context: Structured input data (topic, audience, etc.)
        """
        if not self._current_step:
            logger.warning("No active stage to log prompt")
            return

        self._current_step.prompt_system = system_prompt
        self._current_step.prompt_user = user_prompt
        self._current_step.input_context = input_context

        self.db.commit()

        logger.debug(f"Logged prompt for stage: {self._current_step.stage}")

    def log_response(
        self,
        raw_response: str,
        parsed_result: Any,
        model: str,
        temperature: float = 0.7,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """
        Log the LLM response.

        Args:
            raw_response: Raw text response from LLM
            parsed_result: Parsed/structured result
            model: Model name (e.g., "gpt-4o-mini")
            temperature: Temperature setting used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        if not self._current_step:
            logger.warning("No active stage to log response")
            return

        self._current_step.raw_response = raw_response
        self._current_step.result = parsed_result if isinstance(parsed_result, dict) else {"value": parsed_result}
        self._current_step.model_used = model
        self._current_step.temperature = temperature
        self._current_step.input_tokens = input_tokens
        self._current_step.output_tokens = output_tokens
        self._current_step.tokens_used = input_tokens + output_tokens

        self.db.commit()

        logger.debug(f"Logged response for stage: {self._current_step.stage} (tokens: {input_tokens + output_tokens})")

    def complete_stage(self, duration_seconds: int) -> None:
        """
        Mark stage as completed.

        Args:
            duration_seconds: Time taken for this stage
        """
        if not self._current_step:
            logger.warning("No active stage to complete")
            return

        self._current_step.status = "completed"
        self._current_step.completed_at = datetime.utcnow()
        self._current_step.duration_seconds = duration_seconds

        self.db.commit()

        logger.info(f"Completed stage: {self._current_step.stage} in {duration_seconds}s")
        self._current_step = None

    def fail_stage(self, error_message: str, duration_seconds: int = 0) -> None:
        """
        Mark stage as failed.

        Args:
            error_message: Error description
            duration_seconds: Time taken before failure
        """
        if not self._current_step:
            logger.warning("No active stage to fail")
            return

        self._current_step.status = "failed"
        self._current_step.completed_at = datetime.utcnow()
        self._current_step.error_message = error_message
        self._current_step.duration_seconds = duration_seconds

        self.db.commit()

        logger.error(f"Failed stage: {self._current_step.stage} - {error_message}")
        self._current_step = None

    def get_step_result(self) -> Optional[PipelineStepResult]:
        """Get the current step result being logged."""
        return self._current_step

    @staticmethod
    def get_logs_for_execution(
        db: Session,
        execution_id: int,
        include_prompts: bool = True,
        include_responses: bool = True
    ) -> list:
        """
        Get all logs for a pipeline execution.

        Args:
            db: Database session
            execution_id: Pipeline execution ID
            include_prompts: Include prompt text
            include_responses: Include response text

        Returns:
            List of step results with logs
        """
        steps = db.query(PipelineStepResult).filter(
            PipelineStepResult.execution_id == execution_id
        ).order_by(PipelineStepResult.stage_order).all()

        logs = []
        for step in steps:
            log_entry = {
                "id": step.id,
                "stage": step.stage,
                "stage_order": step.stage_order,
                "status": step.status,
                "duration_seconds": step.duration_seconds,
                "tokens_used": step.tokens_used,
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
                "model_used": step.model_used,
                "temperature": step.temperature,
                "error_message": step.error_message,
                "retry_count": step.retry_count,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }

            if include_prompts:
                log_entry["prompt_system"] = step.prompt_system
                log_entry["prompt_user"] = step.prompt_user
                log_entry["input_context"] = step.input_context

            if include_responses:
                log_entry["raw_response"] = step.raw_response
                log_entry["result"] = step.result

            logs.append(log_entry)

        return logs

    @staticmethod
    def delete_logs_for_execution(db: Session, execution_id: int) -> int:
        """
        Delete all logs for a pipeline execution.

        Args:
            db: Database session
            execution_id: Pipeline execution ID

        Returns:
            Number of logs deleted
        """
        deleted = db.query(PipelineStepResult).filter(
            PipelineStepResult.execution_id == execution_id
        ).delete()

        db.commit()

        logger.info(f"Deleted {deleted} logs for execution {execution_id}")
        return deleted
