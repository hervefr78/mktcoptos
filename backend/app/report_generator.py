"""
Report Generator - Generates comprehensive PDF reports for pipeline executions.

This module creates detailed, professional reports with:
- Executive summary
- Pipeline metrics and visualizations
- Agent-by-agent breakdown
- RAG usage analysis
- Content transformation tracking
- Quality assessments
- Cost analysis
"""
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from jinja2 import Template
from weasyprint import HTML, CSS

from .models import PipelineExecution, AgentActivity
from .agent_activity_tracker import AgentActivityTracker

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates comprehensive reports for pipeline executions.

    Usage:
        generator = ReportGenerator(db)
        pdf_bytes = generator.generate_pdf_report(pipeline_execution_id)

        # Save to file
        with open("report.pdf", "wb") as f:
            f.write(pdf_bytes)
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_pdf_report(self, pipeline_execution_id: int) -> bytes:
        """
        Generate a PDF report for a pipeline execution.

        Args:
            pipeline_execution_id: Pipeline execution ID

        Returns:
            PDF file as bytes
        """
        # Get pipeline execution
        execution = self.db.query(PipelineExecution).filter(
            PipelineExecution.id == pipeline_execution_id
        ).first()

        if not execution:
            raise ValueError(f"Pipeline execution {pipeline_execution_id} not found")

        # Get all agent activities
        activities = AgentActivityTracker.get_activities_for_execution(
            self.db, pipeline_execution_id
        )

        # Generate report data
        report_data = self._prepare_report_data(execution, activities)

        # Generate HTML
        html_content = self._generate_html(report_data)

        # Convert to PDF
        pdf_bytes = self._html_to_pdf(html_content)

        return pdf_bytes

    def _prepare_report_data(
        self,
        execution: PipelineExecution,
        activities: List[AgentActivity]
    ) -> Dict[str, Any]:
        """
        Prepare structured data for the report.

        Args:
            execution: PipelineExecution record
            activities: List of AgentActivity records

        Returns:
            Structured report data
        """
        # Calculate totals
        total_tokens = sum(
            (a.input_tokens or 0) + (a.output_tokens or 0)
            for a in activities
        )
        total_cost = sum(
            float(a.estimated_cost or 0)
            for a in activities
        )

        # Agent breakdown
        agent_breakdown = []
        for activity in activities:
            agent_data = {
                "name": activity.agent_name,
                "stage": activity.stage,
                "status": activity.status,
                "duration": activity.duration_seconds or 0,
                "input_tokens": activity.input_tokens or 0,
                "output_tokens": activity.output_tokens or 0,
                "total_tokens": (activity.input_tokens or 0) + (activity.output_tokens or 0),
                "cost": float(activity.estimated_cost or 0),
                "decisions_count": len(activity.decisions or []),
                "rag_docs_count": len(activity.rag_documents or []),
                "changes_count": len(activity.changes_made or []),
                "warnings_count": len(activity.warnings or []),
                "errors_count": len(activity.errors or []),
                "badges": activity.badges or [],
                "quality_metrics": activity.quality_metrics or {},
                "decisions": activity.decisions or [],
                "rag_documents": activity.rag_documents or [],
                "changes_made": activity.changes_made or [],
            }
            agent_breakdown.append(agent_data)

        # RAG summary
        rag_summary = self._summarize_rag_usage(activities)

        # Timeline
        timeline = self._build_timeline(activities)

        return {
            "execution": {
                "id": execution.id,
                "pipeline_id": execution.pipeline_id,
                "topic": execution.topic,
                "content_type": execution.content_type,
                "audience": execution.audience,
                "status": execution.status,
                "started_at": execution.started_at.strftime("%Y-%m-%d %H:%M:%S") if execution.started_at else None,
                "completed_at": execution.completed_at.strftime("%Y-%m-%d %H:%M:%S") if execution.completed_at else None,
                "duration": execution.total_duration_seconds or 0,
                "word_count": execution.word_count,
                "seo_score": execution.seo_score,
            },
            "metrics": {
                "total_agents": len(activities),
                "total_duration": execution.total_duration_seconds or 0,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "avg_tokens_per_agent": total_tokens / len(activities) if activities else 0,
            },
            "agent_breakdown": agent_breakdown,
            "rag_summary": rag_summary,
            "timeline": timeline,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _summarize_rag_usage(self, activities: List[AgentActivity]) -> Dict[str, Any]:
        """Summarize RAG document usage across all agents."""
        all_docs = {}

        for activity in activities:
            for rag_doc in (activity.rag_documents or []):
                doc_id = rag_doc.get("doc_id")
                doc_name = rag_doc.get("doc_name", "Unknown")

                if doc_id not in all_docs:
                    all_docs[doc_id] = {
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "total_chunks": 0,
                        "used_by_agents": [],
                    }

                all_docs[doc_id]["total_chunks"] += rag_doc.get("chunks_used", 0)
                all_docs[doc_id]["used_by_agents"].append(activity.agent_name)

        return {
            "total_docs_used": len(all_docs),
            "documents": list(all_docs.values()),
        }

    def _build_timeline(self, activities: List[AgentActivity]) -> List[Dict[str, Any]]:
        """Build a chronological timeline of agent executions."""
        timeline = []

        for activity in sorted(activities, key=lambda a: a.started_at):
            timeline.append({
                "agent": activity.agent_name,
                "started": activity.started_at.strftime("%H:%M:%S"),
                "completed": activity.completed_at.strftime("%H:%M:%S") if activity.completed_at else "Running",
                "duration": activity.duration_seconds or 0,
                "status": activity.status,
            })

        return timeline

    def _generate_html(self, report_data: Dict[str, Any]) -> str:
        """
        Generate HTML report with embedded charts.

        Args:
            report_data: Structured report data

        Returns:
            HTML string
        """
        template = Template(self._get_html_template())
        html = template.render(**report_data)
        return html

    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF using WeasyPrint.

        Args:
            html_content: HTML string

        Returns:
            PDF as bytes
        """
        pdf_buffer = io.BytesIO()

        # Generate PDF
        HTML(string=html_content).write_pdf(
            pdf_buffer,
            stylesheets=[CSS(string=self._get_pdf_styles())]
        )

        pdf_buffer.seek(0)
        return pdf_buffer.read()

    def _get_html_template(self) -> str:
        """Get the HTML template for the report."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Execution Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="report-container">
        <!-- Header -->
        <header class="report-header">
            <h1>Pipeline Execution Report</h1>
            <p class="subtitle">Generated on {{ generated_at }}</p>
        </header>

        <!-- Executive Summary -->
        <section class="executive-summary">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="metric-card">
                    <h3>Pipeline ID</h3>
                    <p class="metric-value">{{ execution.pipeline_id }}</p>
                </div>
                <div class="metric-card">
                    <h3>Topic</h3>
                    <p class="metric-value">{{ execution.topic }}</p>
                </div>
                <div class="metric-card">
                    <h3>Status</h3>
                    <p class="metric-value status-{{ execution.status }}">{{ execution.status|upper }}</p>
                </div>
                <div class="metric-card">
                    <h3>Duration</h3>
                    <p class="metric-value">{{ "%.1f"|format(execution.duration) }}s</p>
                </div>
                <div class="metric-card">
                    <h3>Total Tokens</h3>
                    <p class="metric-value">{{ "{:,}".format(metrics.total_tokens) }}</p>
                </div>
                <div class="metric-card">
                    <h3>Total Cost</h3>
                    <p class="metric-value">${{ "%.4f"|format(metrics.total_cost) }}</p>
                </div>
                <div class="metric-card">
                    <h3>Agents</h3>
                    <p class="metric-value">{{ metrics.total_agents }}</p>
                </div>
                {% if execution.word_count %}
                <div class="metric-card">
                    <h3>Word Count</h3>
                    <p class="metric-value">{{ "{:,}".format(execution.word_count) }}</p>
                </div>
                {% endif %}
            </div>
        </section>

        <!-- Agent Breakdown -->
        <section class="agent-breakdown">
            <h2>Agent Performance</h2>
            {% for agent in agent_breakdown %}
            <div class="agent-card">
                <div class="agent-header">
                    <h3>{{ agent.name }}</h3>
                    <span class="agent-status status-{{ agent.status }}">{{ agent.status|upper }}</span>
                </div>
                <div class="agent-metrics">
                    <div class="metric">
                        <span class="label">Duration:</span>
                        <span class="value">{{ "%.2f"|format(agent.duration) }}s</span>
                    </div>
                    <div class="metric">
                        <span class="label">Tokens:</span>
                        <span class="value">{{ "{:,}".format(agent.total_tokens) }}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Cost:</span>
                        <span class="value">${{ "%.4f"|format(agent.cost) }}</span>
                    </div>
                </div>

                {% if agent.decisions %}
                <div class="agent-section">
                    <h4>Decisions ({{ agent.decisions_count }})</h4>
                    <ul class="decision-list">
                        {% for decision in agent.decisions %}
                        <li>{{ decision.description }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if agent.rag_documents %}
                <div class="agent-section">
                    <h4>RAG Documents Used ({{ agent.rag_docs_count }})</h4>
                    <ul class="rag-list">
                        {% for doc in agent.rag_documents %}
                        <li>
                            <strong>{{ doc.doc_name }}</strong> -
                            {{ doc.chunks_used }} chunks
                            {% if doc.purpose %}({{ doc.purpose }}){% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if agent.changes_made %}
                <div class="agent-section">
                    <h4>Changes Made ({{ agent.changes_count }})</h4>
                    <ul class="changes-list">
                        {% for change in agent.changes_made %}
                        <li>
                            <strong>{{ change.type }}:</strong>
                            {% if change.reason %}{{ change.reason }}{% endif %}
                            {% if change.location %}<em>({{ change.location }})</em>{% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if agent.badges %}
                <div class="agent-section">
                    <h4>Badges</h4>
                    <div class="badges">
                        {% for badge in agent.badges %}
                        <span class="badge">{{ badge.name }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </section>

        <!-- RAG Summary -->
        {% if rag_summary.total_docs_used > 0 %}
        <section class="rag-summary">
            <h2>RAG Document Usage</h2>
            <p>Total documents used: <strong>{{ rag_summary.total_docs_used }}</strong></p>
            <table class="rag-table">
                <thead>
                    <tr>
                        <th>Document</th>
                        <th>Total Chunks</th>
                        <th>Used By</th>
                    </tr>
                </thead>
                <tbody>
                    {% for doc in rag_summary.documents %}
                    <tr>
                        <td>{{ doc.doc_name }}</td>
                        <td>{{ doc.total_chunks }}</td>
                        <td>{{ doc.used_by_agents|join(", ") }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>
        {% endif %}

        <!-- Timeline -->
        <section class="timeline">
            <h2>Execution Timeline</h2>
            <table class="timeline-table">
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Started</th>
                        <th>Completed</th>
                        <th>Duration (s)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for event in timeline %}
                    <tr>
                        <td>{{ event.agent }}</td>
                        <td>{{ event.started }}</td>
                        <td>{{ event.completed }}</td>
                        <td>{{ "%.2f"|format(event.duration) }}</td>
                        <td><span class="status-{{ event.status }}">{{ event.status|upper }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <!-- Footer -->
        <footer class="report-footer">
            <p>Marketing Assistant - Pipeline Execution Report</p>
            <p>Execution ID: {{ execution.id }} | Pipeline ID: {{ execution.pipeline_id }}</p>
        </footer>
    </div>
</body>
</html>
"""

    def _get_pdf_styles(self) -> str:
        """Get CSS styles for PDF rendering."""
        return """
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #333;
}

.report-container {
    max-width: 100%;
}

.report-header {
    text-align: center;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 1em;
    margin-bottom: 2em;
}

.report-header h1 {
    font-size: 24pt;
    margin: 0 0 0.5em 0;
    color: #1e40af;
}

.subtitle {
    color: #6b7280;
    margin: 0;
}

section {
    margin-bottom: 2em;
    page-break-inside: avoid;
}

h2 {
    font-size: 16pt;
    color: #1e40af;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 0.3em;
    margin-bottom: 1em;
}

h3 {
    font-size: 12pt;
    margin: 0.5em 0;
}

h4 {
    font-size: 11pt;
    color: #4b5563;
    margin: 0.8em 0 0.4em 0;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1em;
    margin-bottom: 2em;
}

.metric-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    padding: 1em;
    text-align: center;
}

.metric-card h3 {
    font-size: 9pt;
    color: #6b7280;
    margin: 0 0 0.5em 0;
    text-transform: uppercase;
}

.metric-value {
    font-size: 14pt;
    font-weight: bold;
    color: #111827;
    margin: 0;
}

.agent-card {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 1.2em;
    margin-bottom: 1.5em;
    page-break-inside: avoid;
}

.agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1em;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5em;
}

.agent-status {
    padding: 0.3em 0.8em;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: bold;
}

.status-completed {
    background: #d1fae5;
    color: #065f46;
}

.status-running {
    background: #dbeafe;
    color: #1e40af;
}

.status-failed {
    background: #fee2e2;
    color: #991b1b;
}

.agent-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1em;
    margin-bottom: 1em;
}

.metric {
    font-size: 9pt;
}

.metric .label {
    color: #6b7280;
    font-weight: 600;
}

.metric .value {
    color: #111827;
    font-weight: bold;
    margin-left: 0.3em;
}

.agent-section {
    margin-top: 1em;
    padding-top: 0.8em;
    border-top: 1px solid #f3f4f6;
}

.decision-list, .rag-list, .changes-list {
    margin: 0.5em 0;
    padding-left: 1.5em;
    font-size: 9pt;
}

.decision-list li, .rag-list li, .changes-list li {
    margin-bottom: 0.3em;
}

.badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5em;
}

.badge {
    background: #fef3c7;
    color: #92400e;
    padding: 0.3em 0.6em;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 600;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1em;
    font-size: 9pt;
}

th {
    background: #f3f4f6;
    color: #374151;
    font-weight: 600;
    text-align: left;
    padding: 0.6em;
    border-bottom: 2px solid #d1d5db;
}

td {
    padding: 0.6em;
    border-bottom: 1px solid #e5e7eb;
}

tr:hover {
    background: #f9fafb;
}

.report-footer {
    text-align: center;
    margin-top: 3em;
    padding-top: 1em;
    border-top: 2px solid #e5e7eb;
    color: #6b7280;
    font-size: 8pt;
}

.report-footer p {
    margin: 0.3em 0;
}
"""
