"""
Agent Activity Tracker - Comprehensive tracking for agent actions during pipeline execution.

This tracker provides real-time monitoring and logging of:
- Agent decisions and reasoning
- RAG document usage
- Content transformations (before/after)
- Performance metrics
- LLM usage and costs
- Quality assessments
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from .models import AgentActivity

logger = logging.getLogger(__name__)


class AgentActivityTracker:
    """
    Tracks comprehensive activity for individual agents during pipeline execution.

    Usage:
        tracker = AgentActivityTracker(db, pipeline_execution_id)

        # Start tracking an agent
        tracker.start_agent("SEO Optimizer", "seo_optimizer")

        # Log decisions in real-time
        tracker.log_decision("Identified 5 high-value keywords to add")

        # Log RAG usage
        tracker.log_rag_usage(doc_id=123, doc_name="Brand Voice.pdf", chunks_used=3)

        # Log content changes
        tracker.log_content_change(
            content_before="Original title",
            content_after="Optimized title with keywords",
            change_type="title_optimization"
        )

        # Complete tracking
        tracker.complete_agent(
            output_summary={"seo_score": 85, "keywords_added": 5},
            quality_metrics={"readability": 90, "keyword_density": 3.2}
        )
    """

    def __init__(self, db: Session, pipeline_execution_id: int):
        self.db = db
        self.pipeline_execution_id = pipeline_execution_id
        self._current_activity: Optional[AgentActivity] = None
        self._start_time: Optional[datetime] = None

    def start_agent(
        self,
        agent_name: str,
        stage: str,
        input_summary: Optional[Dict[str, Any]] = None
    ) -> AgentActivity:
        """
        Start tracking a new agent execution.

        Args:
            agent_name: Human-readable agent name (e.g., "SEO Optimizer")
            stage: Stage identifier (e.g., "seo_optimizer")
            input_summary: Summary of input data

        Returns:
            The created AgentActivity record
        """
        self._start_time = datetime.utcnow()

        self._current_activity = AgentActivity(
            pipeline_execution_id=self.pipeline_execution_id,
            agent_name=agent_name,
            stage=stage,
            started_at=self._start_time,
            status="running",
            input_summary=input_summary or {},
            decisions=[],
            rag_documents=[],
            changes_made=[],
            warnings=[],
            errors=[],
            badges=[]
        )

        self.db.add(self._current_activity)
        self.db.commit()
        self.db.refresh(self._current_activity)

        logger.info(f"Started tracking agent: {agent_name} (stage: {stage})")
        return self._current_activity

    def log_decision(self, description: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a decision made by the agent.

        Args:
            description: Description of the decision
            data: Additional structured data about the decision
        """
        if not self._current_activity:
            logger.warning("No active agent to log decision")
            return

        decision = {
            "timestamp": datetime.utcnow().isoformat(),
            "description": description,
            "data": data or {}
        }

        # Append to decisions array
        if self._current_activity.decisions is None:
            self._current_activity.decisions = []

        decisions = list(self._current_activity.decisions)
        decisions.append(decision)
        self._current_activity.decisions = decisions

        self.db.commit()
        logger.debug(f"Logged decision for {self._current_activity.agent_name}: {description}")

    def log_rag_usage(
        self,
        doc_id: int,
        doc_name: str,
        chunks_used: int,
        influence_score: Optional[float] = None,
        purpose: Optional[str] = None
    ) -> None:
        """
        Log RAG document usage by the agent.

        Args:
            doc_id: Document ID
            doc_name: Document filename
            chunks_used: Number of chunks retrieved
            influence_score: How much this doc influenced the output (0-1)
            purpose: Why this document was used
        """
        if not self._current_activity:
            logger.warning("No active agent to log RAG usage")
            return

        rag_entry = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "chunks_used": chunks_used,
            "influence_score": influence_score,
            "purpose": purpose,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Append to rag_documents array
        if self._current_activity.rag_documents is None:
            self._current_activity.rag_documents = []

        rag_docs = list(self._current_activity.rag_documents)
        rag_docs.append(rag_entry)
        self._current_activity.rag_documents = rag_docs

        self.db.commit()
        logger.debug(f"Logged RAG usage for {self._current_activity.agent_name}: {doc_name}")

    def log_content_change(
        self,
        change_type: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        reason: Optional[str] = None,
        location: Optional[str] = None
    ) -> None:
        """
        Log a content transformation made by the agent.

        Args:
            change_type: Type of change (e.g., "keyword_insertion", "title_rewrite")
            before: Content before change
            after: Content after change
            reason: Why the change was made
            location: Where in the content (e.g., "paragraph 3")
        """
        if not self._current_activity:
            logger.warning("No active agent to log content change")
            return

        change = {
            "type": change_type,
            "before": before,
            "after": after,
            "reason": reason,
            "location": location,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Append to changes_made array
        if self._current_activity.changes_made is None:
            self._current_activity.changes_made = []

        changes = list(self._current_activity.changes_made)
        changes.append(change)
        self._current_activity.changes_made = changes

        self.db.commit()
        logger.debug(f"Logged content change for {self._current_activity.agent_name}: {change_type}")

    def set_content_before_after(self, content_before: str, content_after: str) -> None:
        """
        Set the full before/after content for optimization agents.

        Args:
            content_before: Full content before optimization
            content_after: Full content after optimization
        """
        if not self._current_activity:
            logger.warning("No active agent to set content")
            return

        self._current_activity.content_before = content_before
        self._current_activity.content_after = content_after

        self.db.commit()

    def log_llm_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float = 0.0
    ) -> None:
        """
        Log LLM usage metrics.

        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            estimated_cost: Estimated cost in USD
        """
        if not self._current_activity:
            logger.warning("No active agent to log LLM usage")
            return

        self._current_activity.model_used = model
        self._current_activity.input_tokens = input_tokens
        self._current_activity.output_tokens = output_tokens
        self._current_activity.estimated_cost = Decimal(str(estimated_cost))

        self.db.commit()

    def add_warning(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a warning message.

        Args:
            message: Warning message
            data: Additional data about the warning
        """
        if not self._current_activity:
            logger.warning("No active agent to add warning")
            return

        warning = {
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        if self._current_activity.warnings is None:
            self._current_activity.warnings = []

        warnings = list(self._current_activity.warnings)
        warnings.append(warning)
        self._current_activity.warnings = warnings

        self.db.commit()
        logger.warning(f"Warning for {self._current_activity.agent_name}: {message}")

    def add_error(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an error message.

        Args:
            message: Error message
            data: Additional data about the error
        """
        if not self._current_activity:
            logger.warning("No active agent to add error")
            return

        error = {
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        if self._current_activity.errors is None:
            self._current_activity.errors = []

        errors = list(self._current_activity.errors)
        errors.append(error)
        self._current_activity.errors = errors

        self.db.commit()
        logger.error(f"Error for {self._current_activity.agent_name}: {message}")

    def add_badge(self, badge_name: str, badge_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a quality badge (e.g., "SEO_OPTIMIZED", "FACTUALLY_GROUNDED").

        Args:
            badge_name: Badge identifier
            badge_data: Additional badge metadata
        """
        if not self._current_activity:
            logger.warning("No active agent to add badge")
            return

        badge = {
            "name": badge_name,
            "data": badge_data or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        if self._current_activity.badges is None:
            self._current_activity.badges = []

        badges = list(self._current_activity.badges)
        badges.append(badge)
        self._current_activity.badges = badges

        self.db.commit()

    def complete_agent(
        self,
        output_summary: Optional[Dict[str, Any]] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
        performance_breakdown: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark agent execution as completed.

        Args:
            output_summary: Summary of agent output
            quality_metrics: Quality assessment metrics
            performance_breakdown: Detailed performance metrics
        """
        if not self._current_activity:
            logger.warning("No active agent to complete")
            return

        completed_at = datetime.utcnow()
        duration = (completed_at - self._start_time).total_seconds() if self._start_time else 0

        self._current_activity.status = "completed"
        self._current_activity.completed_at = completed_at
        self._current_activity.duration_seconds = duration
        self._current_activity.output_summary = output_summary or {}
        self._current_activity.quality_metrics = quality_metrics or {}
        self._current_activity.performance_breakdown = performance_breakdown or {}

        self.db.commit()

        logger.info(
            f"Completed agent: {self._current_activity.agent_name} "
            f"in {duration:.2f}s"
        )
        self._current_activity = None
        self._start_time = None

    def fail_agent(self, error_message: str) -> None:
        """
        Mark agent execution as failed.

        Args:
            error_message: Error description
        """
        if not self._current_activity:
            logger.warning("No active agent to fail")
            return

        completed_at = datetime.utcnow()
        duration = (completed_at - self._start_time).total_seconds() if self._start_time else 0

        self._current_activity.status = "failed"
        self._current_activity.completed_at = completed_at
        self._current_activity.duration_seconds = duration

        # Add to errors list
        self.add_error(error_message)

        self.db.commit()

        logger.error(
            f"Failed agent: {self._current_activity.agent_name} - {error_message}"
        )
        self._current_activity = None
        self._start_time = None

    def get_current_activity(self) -> Optional[AgentActivity]:
        """Get the current activity being tracked."""
        return self._current_activity

    @staticmethod
    def get_activities_for_execution(
        db: Session,
        pipeline_execution_id: int
    ) -> List[AgentActivity]:
        """
        Get all agent activities for a pipeline execution.

        Args:
            db: Database session
            pipeline_execution_id: Pipeline execution ID

        Returns:
            List of AgentActivity records
        """
        activities = db.query(AgentActivity).filter(
            AgentActivity.pipeline_execution_id == pipeline_execution_id
        ).order_by(AgentActivity.started_at).all()

        return activities
