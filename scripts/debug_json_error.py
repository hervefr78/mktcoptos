#!/usr/bin/env python3
"""
Debug script to investigate JSON parsing errors in the content pipeline.
Shows the raw LLM response that failed to parse.

Usage:
    python scripts/debug_json_error.py
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path to import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database import SessionLocal
from backend.app.models import PipelineExecution, AgentStepResult
from sqlalchemy import desc


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"{'=' * 80}\n")


def show_latest_json_errors(limit=5):
    """Show the most recent JSON parsing errors."""
    db = SessionLocal()

    try:
        # Find recent failed executions with JSON errors
        print_separator("SEARCHING FOR RECENT JSON PARSING ERRORS")

        recent_executions = db.query(PipelineExecution).filter(
            PipelineExecution.status == 'failed',
            PipelineExecution.error_message.ilike('%json%')
        ).order_by(desc(PipelineExecution.created_at)).limit(limit).all()

        if not recent_executions:
            print("❌ No recent JSON parsing errors found in the last executions.")
            print("\nTrying to find ANY failed executions...")

            recent_executions = db.query(PipelineExecution).filter(
                PipelineExecution.status == 'failed'
            ).order_by(desc(PipelineExecution.created_at)).limit(limit).all()

            if not recent_executions:
                print("❌ No failed executions found at all.")
                return

        print(f"✅ Found {len(recent_executions)} failed execution(s) with errors\n")

        for i, execution in enumerate(recent_executions, 1):
            print_separator(f"EXECUTION #{i} - ID: {execution.id}")

            print(f"📅 Created:      {execution.created_at}")
            print(f"📝 Topic:        {execution.topic or 'N/A'}")
            print(f"🎯 Content Type: {execution.content_type or 'N/A'}")
            print(f"❌ Status:       {execution.status}")
            print(f"🔴 Error Stage:  {execution.error_stage or 'N/A'}")
            print(f"⚠️  Error:        {execution.error_message or 'N/A'}")

            # Get the agent step results for this execution
            print("\n📊 AGENT STEP RESULTS:")
            print("-" * 80)

            step_results = db.query(AgentStepResult).filter(
                AgentStepResult.pipeline_execution_id == execution.id
            ).order_by(AgentStepResult.id).all()

            if not step_results:
                print("  No agent step results found.")

            for step in step_results:
                status_emoji = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
                print(f"\n  {status_emoji} {step.agent_name} ({step.stage})")
                print(f"     Status: {step.status}")

                if step.status == "failed" and step.error_message:
                    print(f"     Error: {step.error_message}")

                # Show raw response if it exists
                if step.raw_llm_response:
                    print(f"\n     📄 RAW LLM RESPONSE (first 2000 chars):")
                    print("     " + "-" * 76)
                    raw_preview = step.raw_llm_response[:2000]
                    for line in raw_preview.split('\n'):
                        print(f"     {line}")
                    if len(step.raw_llm_response) > 2000:
                        print(f"     ... (truncated, total length: {len(step.raw_llm_response)} chars)")
                    print("     " + "-" * 76)

                    # Try to identify the JSON parsing issue
                    if "json" in step.error_message.lower() if step.error_message else "":
                        print(f"\n     🔍 ATTEMPTING TO IDENTIFY JSON ERROR:")
                        try:
                            json.loads(step.raw_llm_response)
                            print(f"     ✅ JSON is actually valid! May be an issue with extraction.")
                        except json.JSONDecodeError as e:
                            print(f"     ❌ JSON Error at line {e.lineno}, column {e.colno}: {e.msg}")
                            print(f"     Character position: {e.pos}")

                            # Show context around the error
                            if e.pos and e.pos < len(step.raw_llm_response):
                                start = max(0, e.pos - 100)
                                end = min(len(step.raw_llm_response), e.pos + 100)
                                context = step.raw_llm_response[start:end]
                                print(f"\n     📍 CONTEXT AROUND ERROR:")
                                print("     " + "-" * 76)
                                for line in context.split('\n'):
                                    print(f"     {line}")
                                print("     " + "-" * 76)

                if step.parsed_result:
                    print(f"\n     ✅ Parsed result exists: {list(step.parsed_result.keys()) if isinstance(step.parsed_result, dict) else type(step.parsed_result)}")

            print("\n")

    finally:
        db.close()


def show_specific_execution(execution_id):
    """Show details for a specific execution ID."""
    db = SessionLocal()

    try:
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.id == execution_id
        ).first()

        if not execution:
            print(f"❌ Execution ID {execution_id} not found.")
            return

        print_separator(f"EXECUTION DETAILS - ID: {execution_id}")

        print(f"📅 Created:      {execution.created_at}")
        print(f"📝 Topic:        {execution.topic or 'N/A'}")
        print(f"🎯 Content Type: {execution.content_type or 'N/A'}")
        print(f"❌ Status:       {execution.status}")
        print(f"🔴 Error Stage:  {execution.error_stage or 'N/A'}")
        print(f"⚠️  Error:        {execution.error_message or 'N/A'}")

        # Get the agent step results
        print("\n📊 AGENT STEP RESULTS:")
        print("-" * 80)

        step_results = db.query(AgentStepResult).filter(
            AgentStepResult.pipeline_execution_id == execution_id
        ).order_by(AgentStepResult.id).all()

        for step in step_results:
            status_emoji = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
            print(f"\n  {status_emoji} {step.agent_name} ({step.stage})")
            print(f"     Status: {step.status}")

            if step.status == "failed" and step.error_message:
                print(f"     Error: {step.error_message}")

            if step.raw_llm_response:
                print(f"\n     📄 FULL RAW LLM RESPONSE:")
                print("     " + "-" * 76)
                for line in step.raw_llm_response.split('\n'):
                    print(f"     {line}")
                print("     " + "-" * 76)

    finally:
        db.close()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Specific execution ID provided
        try:
            execution_id = int(sys.argv[1])
            show_specific_execution(execution_id)
        except ValueError:
            print(f"❌ Invalid execution ID: {sys.argv[1]}")
            print("Usage: python scripts/debug_json_error.py [execution_id]")
            sys.exit(1)
    else:
        # Show latest errors
        show_latest_json_errors(limit=3)


if __name__ == "__main__":
    main()
