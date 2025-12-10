"""
Debug routes for viewing pipeline execution logs and agent activities
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, cast, Text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from .database import get_db
from .models import PipelineExecution, AgentActivity, PipelineStepResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


def safe_json_field(value: Any) -> Any:
    """Safely handle JSON fields that might be strings or None"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


@router.get("/pipeline-executions")
async def get_pipeline_executions(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent pipeline executions with their basic info and errors.

    Query parameters:
    - limit: Number of records to return (1-200, default 50)
    - status: Filter by status (pending, running, completed, failed)
    """
    try:
        query = db.query(PipelineExecution).order_by(desc(PipelineExecution.created_at))

        if status:
            query = query.filter(PipelineExecution.status == status)

        executions = query.limit(limit).all()

        return {
            "success": True,
            "count": len(executions),
            "executions": [
                {
                    "id": ex.id,
                    "pipeline_id": ex.pipeline_id,
                    "topic": ex.topic,
                    "content_type": ex.content_type,
                    "status": ex.status,
                    "current_stage": ex.current_stage,
                    "error_message": ex.error_message,
                    "error_stage": ex.error_stage,
                    "total_duration_seconds": ex.total_duration_seconds,
                    "total_tokens_used": ex.total_tokens_used,
                    "estimated_cost": float(ex.estimated_cost) if ex.estimated_cost else 0.0,
                    "word_count": ex.word_count,
                    "seo_score": ex.seo_score,
                    "originality_score": ex.originality_score,
                    "started_at": ex.started_at.isoformat() if ex.started_at else None,
                    "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                    "stage_summaries": safe_json_field(ex.stage_summaries),
                }
                for ex in executions
            ]
        }
    except Exception as e:
        logger.exception("Error fetching executions")
        raise HTTPException(status_code=500, detail=f"Error fetching executions: {str(e)}")


@router.get("/agent-activities")
async def get_agent_activities(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent agent activities with their decisions and errors.

    Query parameters:
    - limit: Number of records to return (1-200, default 50)
    - status: Filter by status (running, completed, failed)
    """
    try:
        query = db.query(AgentActivity).order_by(desc(AgentActivity.started_at))

        if status:
            query = query.filter(AgentActivity.status == status)

        activities = query.limit(limit).all()

        return {
            "success": True,
            "count": len(activities),
            "activities": [
                {
                    "id": a.id,
                    "pipeline_execution_id": a.pipeline_execution_id,
                    "agent_name": a.agent_name,
                    "stage": a.stage,
                    "status": a.status,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "duration_seconds": a.duration_seconds,
                    "decisions": safe_json_field(a.decisions),
                    "rag_documents": safe_json_field(a.rag_documents),
                    "changes_made": safe_json_field(a.changes_made),
                    "input_summary": safe_json_field(a.input_summary),
                    "output_summary": safe_json_field(a.output_summary),
                    "tokens_used": (a.input_tokens or 0) + (a.output_tokens or 0),
                    "estimated_cost": float(a.estimated_cost) if a.estimated_cost else 0.0,
                    "quality_metrics": safe_json_field(a.quality_metrics),
                    "llm_calls": a.llm_calls,
                    "cache_hits": a.cache_hits,
                    "errors": safe_json_field(a.errors),
                    "warnings": safe_json_field(a.warnings),
                    "badges": safe_json_field(a.badges),
                }
                for a in activities
            ]
        }
    except Exception as e:
        logger.exception("Error fetching activities")
        raise HTTPException(status_code=500, detail=f"Error fetching activities: {str(e)}")


@router.get("/execution/{execution_id}/full")
async def get_execution_full_details(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete details for a specific pipeline execution including:
    - Pipeline execution record
    - All agent activities
    - All step results
    """
    try:
        # Get pipeline execution
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Get agent activities
        activities = db.query(AgentActivity).filter(
            AgentActivity.pipeline_execution_id == execution_id
        ).order_by(AgentActivity.started_at).all()

        # Get step results
        steps = db.query(PipelineStepResult).filter(
            PipelineStepResult.execution_id == execution_id
        ).order_by(PipelineStepResult.stage_order).all()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Database error while fetching execution details")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    try:
        return {
            "success": True,
            "execution": {
                "id": execution.id,
                "pipeline_id": execution.pipeline_id,
                "topic": execution.topic,
                "content_type": execution.content_type,
                "status": execution.status,
                "current_stage": execution.current_stage,
                "error_message": execution.error_message,
                "error_stage": execution.error_stage,
                "total_duration_seconds": execution.total_duration_seconds,
                "total_tokens_used": execution.total_tokens_used,
                "estimated_cost": float(execution.estimated_cost) if execution.estimated_cost else 0.0,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "stage_summaries": safe_json_field(execution.stage_summaries),
                "final_result": safe_json_field(execution.final_result),
            },
            "activities": [
                {
                    "id": a.id,
                    "agent_name": a.agent_name,
                    "stage": a.stage,
                    "status": a.status,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "duration_seconds": a.duration_seconds,
                    "decisions": safe_json_field(a.decisions),
                    "rag_documents": safe_json_field(a.rag_documents),
                    "changes_made": safe_json_field(a.changes_made),
                    "errors": safe_json_field(a.errors),
                    "warnings": safe_json_field(a.warnings),
                    "tokens_used": (a.input_tokens or 0) + (a.output_tokens or 0),
                    "estimated_cost": float(a.estimated_cost) if a.estimated_cost else 0.0,
                }
                for a in activities
            ],
            "steps": [
                {
                    "id": s.id,
                    "stage": s.stage,
                    "stage_order": s.stage_order,
                    "status": s.status,
                    "result": safe_json_field(s.result),
                    "error_message": s.error_message,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in steps
            ]
        }
    except Exception as e:
        logger.exception("Serialization error while building execution details response")
        raise HTTPException(status_code=500, detail=f"Serialization error: {str(e)}")


@router.get("/errors/recent")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Get all errors from the last N hours.

    Query parameters:
    - hours: Number of hours to look back (1-168, default 24)
    """
    try:
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get failed pipeline executions
        failed_executions = db.query(PipelineExecution).filter(
            PipelineExecution.status == "failed",
            PipelineExecution.created_at >= since
        ).order_by(desc(PipelineExecution.created_at)).all()

        # Get agent activities with errors (check if errors array is not empty)
        failed_activities = db.query(AgentActivity).filter(
            AgentActivity.errors.isnot(None),
            cast(AgentActivity.errors, Text) != '[]',
            AgentActivity.started_at >= since
        ).order_by(desc(AgentActivity.started_at)).all()

        # Get executions with warnings (error_message set but status != failed)
        warning_executions = db.query(PipelineExecution).filter(
            PipelineExecution.error_message.isnot(None),
            PipelineExecution.status != "failed",
            PipelineExecution.created_at >= since
        ).order_by(desc(PipelineExecution.created_at)).all()

        return {
            "success": True,
            "time_range_hours": hours,
            "since": since.isoformat(),
            "summary": {
                "failed_executions": len(failed_executions),
                "failed_activities": len(failed_activities),
                "executions_with_warnings": len(warning_executions),
            },
            "failed_executions": [
                {
                    "id": ex.id,
                    "pipeline_id": ex.pipeline_id,
                    "topic": ex.topic,
                    "error_stage": ex.error_stage,
                    "error_message": ex.error_message,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                }
                for ex in failed_executions
            ],
            "failed_activities": [
                {
                    "id": a.id,
                    "pipeline_execution_id": a.pipeline_execution_id,
                    "agent_name": a.agent_name,
                    "stage": a.stage,
                    "errors": safe_json_field(a.errors),
                    "warnings": safe_json_field(a.warnings),
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                }
                for a in failed_activities
            ],
            "executions_with_warnings": [
                {
                    "id": ex.id,
                    "pipeline_id": ex.pipeline_id,
                    "topic": ex.topic,
                    "status": ex.status,
                    "current_stage": ex.current_stage,
                    "error_message": ex.error_message,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                }
                for ex in warning_executions
            ]
        }
    except Exception as e:
        logger.exception("Error fetching recent errors")
        raise HTTPException(status_code=500, detail=f"Error fetching recent errors: {str(e)}")
