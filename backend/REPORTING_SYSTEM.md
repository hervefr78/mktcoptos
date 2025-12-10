# Agent Activity Tracking & Reporting System

## Status: ✅ FULLY IMPLEMENTED AND DEPLOYED

## Overview

This system provides comprehensive tracking and reporting for AI agent activities during pipeline execution. It captures detailed metrics, decisions, RAG usage, content transformations, and generates professional PDF reports with an interactive frontend UI.

## Components

### 1. Database Migration

**Files:**
- `alembic/versions/013_add_agent_activities.py` - Alembic migration (runs automatically)
- `migrations/add_agent_activities.sql` - Standalone SQL migration (manual)

Creates the `agent_activities` table with comprehensive tracking fields:
- Execution tracking (duration, status, timestamps)
- Input/output summaries
- Real-time decisions array
- RAG document usage tracking
- Content before/after comparisons
- Performance metrics
- LLM usage and costs
- Quality metrics and badges
- Diagnostics (warnings, errors)

**Migration runs automatically on startup via Alembic!**

The entrypoint.sh script automatically runs `alembic upgrade head` when the backend container starts, so no manual migration is needed.

**Manual migration (if needed):**
```bash
# Using psql
psql -h localhost -p 5433 -U marketer_user -d marketer_db -f backend/migrations/add_agent_activities.sql

# Or using Docker
docker exec -i marketer_postgres psql -U marketer_user -d marketer_db < backend/migrations/add_agent_activities.sql
```

### 2. AgentActivityTracker

**File:** `app/agent_activity_tracker.py`

Real-time activity tracking for individual agents.

**Usage:**
```python
from app.agent_activity_tracker import AgentActivityTracker

# Initialize tracker
tracker = AgentActivityTracker(db, pipeline_execution_id)

# Start tracking an agent
tracker.start_agent("SEO Optimizer", "seo_optimizer", input_summary={...})

# Log decisions in real-time
tracker.log_decision("Identified 5 high-value keywords to add")

# Log RAG usage
tracker.log_rag_usage(
    doc_id=123,
    doc_name="Brand Voice.pdf",
    chunks_used=3,
    purpose="Extract tone guidelines"
)

# Log content changes
tracker.log_content_change(
    change_type="keyword_insertion",
    before="Original text",
    after="Optimized text with keywords",
    reason="Improve SEO score",
    location="paragraph 2"
)

# Log LLM usage
tracker.log_llm_usage(
    model="gpt-4o-mini",
    input_tokens=500,
    output_tokens=1200,
    estimated_cost=0.0015
)

# Add quality badges
tracker.add_badge("SEO_OPTIMIZED", {"score": 85})

# Complete tracking
tracker.complete_agent(
    output_summary={"seo_score": 85, "keywords_added": 5},
    quality_metrics={"readability": 90, "keyword_density": 3.2}
)
```

### 3. ReportGenerator

**File:** `app/report_generator.py`

Generates comprehensive PDF reports with charts and visualizations.

**Features:**
- Executive summary with key metrics
- Agent-by-agent performance breakdown
- RAG document usage analysis
- Content transformation timeline
- Quality assessments and badges
- Cost analysis and token usage
- Professional PDF styling with WeasyPrint

**Usage:**
```python
from app.report_generator import ReportGenerator

generator = ReportGenerator(db)
pdf_bytes = generator.generate_pdf_report(pipeline_execution_id)

# Save to file
with open("report.pdf", "wb") as f:
    f.write(pdf_bytes)
```

### 4. API Endpoints

**✅ Implemented Endpoints:**

#### Get Agent Activities
**Route:** `GET /api/content-pipeline/execution/{execution_id}/activities`

Returns all agent activity data for visualization.

**Example:**
```bash
curl "http://localhost:8000/api/content-pipeline/execution/123/activities"
```

**Response:**
```json
{
  "success": true,
  "execution_id": 123,
  "activities": [
    {
      "id": 1,
      "agent_name": "Trends & Keywords Agent",
      "stage": "trends_keywords",
      "status": "completed",
      "started_at": "2025-11-28T10:00:00",
      "completed_at": "2025-11-28T10:01:30",
      "duration_seconds": 90,
      "decisions": [...],
      "rag_documents": [...],
      "tokens_used": 2500,
      "estimated_cost": 0.015,
      "quality_metrics": {...}
    }
  ]
}
```

#### Download PDF Report
**Route:** `GET /api/content-pipeline/execution/{execution_id}/report`

Generates and downloads a PDF report for a pipeline execution.

**Example:**
```bash
curl -O "http://localhost:8000/api/content-pipeline/execution/123/report"
```

**Response:**
- Content-Type: `application/pdf`
- Downloads as: `pipeline_{pipeline_id}_report.pdf`

### 5. Frontend UI

**✅ Fully Implemented:**

#### AgentActivitiesTab Component
**File:** `frontend/src/components/ContentWizard/AgentActivitiesTab.jsx`

Interactive React component displaying comprehensive agent activity data:

**Features:**
- **Summary Header**: Shows total agents, duration, tokens, cost, decisions, RAG docs
- **Expandable Agent List**: Click any agent to see details
- **Four Detail Tabs per Agent**:
  1. **Overview**: Output summary, quality metrics, input context
  2. **Decisions**: All decisions made during execution
  3. **RAG**: Documents used with influence scores and purposes
  4. **Changes**: Content transformations with before/after
- **PDF Download Button**: Download detailed report
- **Real-time Loading States**: Shows loading spinners while fetching data
- **Error Handling**: Graceful error messages if data unavailable

#### API Service Layer
**File:** `frontend/src/services/agentActivitiesApi.js`

Service layer for backend communication:

```javascript
import { agentActivitiesApi } from '../services/agentActivitiesApi';

// Get activities
const activities = await agentActivitiesApi.getActivities(executionId);

// Get summary statistics
const summary = await agentActivitiesApi.getSummary(executionId);

// Download PDF
await agentActivitiesApi.downloadReport(executionId, pipelineId);
```

#### Integration in Review Page
**File:** `frontend/src/components/ContentWizard/StepReview.jsx`

The "AI Agents" tab is now available in the Review page alongside:
- Content
- Images
- SEO
- Metadata
- RAG Analysis
- Timeline
- **AI Agents** ← New!

## Dependencies

### Python Packages
The system requires the following Python packages (already added to `requirements.txt`):

```
weasyprint==60.2        # HTML to PDF conversion
jinja2==3.1.3          # HTML templating
```

### System Dependencies (Docker)
WeasyPrint requires system libraries (already added to Dockerfile):

```
libpango-1.0-0          # Pango text layout engine
libpangocairo-1.0-0     # Cairo rendering for Pango
libgdk-pixbuf2.0-0      # Image loading library
libffi-dev              # Foreign Function Interface library
shared-mime-info        # MIME type database
```

**These are automatically installed when building the Docker container.**

**To install locally (Ubuntu/Debian):**
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
pip install -r backend/requirements.txt
```

## Integration with Pipeline Agents

**✅ FULLY INTEGRATED - All 7 agents are now tracked!**

The orchestrator (`app/agents/content_pipeline/orchestrator.py`) has been fully integrated with activity tracking. All 7 pipeline agents now automatically track their activities:

1. **Trends & Keywords Agent** - Tracks keyword research and trend analysis
2. **Tone of Voice Agent** - Tracks brand voice analysis and RAG usage
3. **Structure & Outline Agent** - Tracks outline generation decisions
4. **Content Writer Agent** - Tracks content generation and RAG usage
5. **SEO Optimizer Agent** - Tracks SEO improvements and content transformations
6. **Originality Checker Agent** - Tracks plagiarism checks and quality scores
7. **Final Reviewer Agent** - Tracks final edits and content transformations

### How It Works

The orchestrator initializes the tracker when `db` and `execution_id` are provided:

```python
# In orchestrator.run()
if db and execution_id:
    self.activity_tracker = AgentActivityTracker(db, execution_id)
```

Each `_run_*` method wraps the agent execution with tracking:

```python
async def _run_seo_optimizer(self, state: PipelineState) -> PipelineState:
    # Start tracking
    if self.activity_tracker:
        self.activity_tracker.start_agent("SEO Optimizer", "seo_optimizer", {...})
        self.activity_tracker.log_decision("Analyzing content for SEO improvements...")

        # Set content before transformation
        self.activity_tracker.set_content_before_after(
            content_before=original_content
        )

    try:
        # Run agent...
        result = await self.seo_optimizer_agent.run(...)

        # Log transformations
        if self.activity_tracker:
            self.activity_tracker.set_content_before_after(
                content_after=optimized_content
            )
            self.activity_tracker.log_content_change(
                change_type="seo_optimization",
                before=snippet_before,
                after=snippet_after,
                reason="Improve keyword density",
                location="paragraph 2"
            )

            # Complete tracking
            self.activity_tracker.complete_agent(
                output_summary={"seo_score": 85},
                quality_metrics={"keyword_density": 3.2}
            )

    except Exception as e:
        if self.activity_tracker:
            self.activity_tracker.fail_agent(str(e))
        raise
```

### Adding to New Agents

To add tracking to a new agent, follow this pattern:

```python
from app.agent_activity_tracker import AgentActivityTracker

class YourNewAgent:
    def execute(self, db, pipeline_execution_id, input_data):
        # Initialize tracker
        tracker = AgentActivityTracker(db, pipeline_execution_id)

        try:
            # Start tracking
            tracker.start_agent("Your Agent Name", "your_stage", input_summary=input_data)

            # Your agent logic here...
            tracker.log_decision("Made an important decision")

            # If using RAG
            tracker.log_rag_usage(
                doc_id=123,
                doc_name="Document.pdf",
                chunks_used=3,
                purpose="Extract insights"
            )

            # Complete successfully
            tracker.complete_agent(
                output_summary={"key": "value"},
                quality_metrics={"score": 95}
            )

        except Exception as e:
            # Mark as failed
            tracker.fail_agent(str(e))
            raise
```

## Report Contents

The generated PDF report includes:

### Executive Summary
- Pipeline ID and topic
- Status and duration
- Total tokens used
- Total cost
- Number of agents
- Word count and SEO score

### Agent Performance
For each agent:
- Duration and status
- Token usage and cost
- Decisions made (with descriptions)
- RAG documents used (with chunk counts)
- Content changes (before/after)
- Quality badges

### RAG Usage Summary
- Total documents used
- Chunks per document
- Which agents used which documents

### Execution Timeline
- Chronological view of agent executions
- Start/completion times
- Duration and status for each agent

## Future Enhancements

Phase 2 features to be implemented:
- Historical comparison charts
- Trend analysis across multiple executions
- Cost optimization recommendations
- Agent performance benchmarking
- Interactive HTML reports (in addition to PDF)

## Troubleshooting

### Migration fails
- Ensure PostgreSQL is running
- Check database credentials
- Verify user has CREATE TABLE permissions

### PDF generation fails
- Ensure WeasyPrint dependencies are installed
- Check for missing system libraries (on Linux: `libpango-1.0-0`, `libpangocairo-1.0-0`)

### Missing data in reports
- Ensure agents are using AgentActivityTracker
- Verify database has agent_activities records
- Check that pipeline execution completed successfully

## Files Created/Modified

### Backend
- ✅ `backend/alembic/versions/013_add_agent_activities.py` - Alembic migration (auto-runs)
- ✅ `backend/migrations/add_agent_activities.sql` - Standalone SQL migration
- ✅ `backend/app/models.py` - Added AgentActivity model
- ✅ `backend/app/agent_activity_tracker.py` - Activity tracking class
- ✅ `backend/app/report_generator.py` - PDF report generation
- ✅ `backend/app/content_pipeline_routes.py` - Added activities & report endpoints
- ✅ `backend/app/agents/content_pipeline/orchestrator.py` - Integrated all 7 agents
- ✅ `backend/requirements.txt` - Added weasyprint and jinja2
- ✅ `backend/Dockerfile` - Added WeasyPrint system dependencies

### Frontend
- ✅ `frontend/src/components/ContentWizard/AgentActivitiesTab.jsx` - Main UI component
- ✅ `frontend/src/services/agentActivitiesApi.js` - API service layer
- ✅ `frontend/src/components/ContentWizard/StepReview.jsx` - Added "AI Agents" tab

### Documentation
- ✅ `backend/REPORTING_SYSTEM.md` - Complete usage guide (this file)
- ✅ `backend/INTEGRATION_NOTES.md` - Integration status and roadmap

## Getting Started

### 1. Start the Application

The system is fully configured and will start automatically:

```bash
# Run the launch script
./launch.sh
```

The launch script will:
- Build the Docker containers (including WeasyPrint dependencies)
- Start all services (PostgreSQL, Redis, Backend, Frontend)
- Run database migrations automatically (including agent_activities table)
- Display service status and access URLs

### 2. Generate Content

Navigate to the Content Wizard and generate a piece of content. The tracking happens automatically in the background.

### 3. View Agent Activities

After generation completes:
1. Go to the **Review** page
2. Click the **"AI Agents"** tab
3. See comprehensive tracking data for all 7 agents
4. Click any agent to expand and view detailed information
5. Download PDF report if needed

### 4. Understanding the Data

The UI shows:
- **Summary**: Total metrics across all agents
- **Agent List**: Status and basic info for each agent
- **Detail Tabs**:
  - **Overview**: What the agent produced and metrics
  - **Decisions**: Step-by-step decision log
  - **RAG**: Which documents influenced the output
  - **Changes**: Content transformations (before/after)

## Testing

To verify the system is working:

```bash
# Check if migration ran successfully
docker exec -it marketer_postgres psql -U marketer_user -d marketer_db -c "\d agent_activities"

# You should see the table structure
```

After running a pipeline:

```bash
# Check if activities were recorded
docker exec -it marketer_postgres psql -U marketer_user -d marketer_db -c "SELECT agent_name, status, duration_seconds FROM agent_activities ORDER BY started_at DESC LIMIT 10;"
```

## Next Steps (Optional Enhancements)

The system is fully functional. Future enhancements could include:

1. **Historical Analytics** - Compare executions over time
2. **Cost Optimization** - Recommendations based on token usage patterns
3. **Performance Benchmarking** - Agent performance metrics across executions
4. **Advanced Visualizations** - Charts and graphs for trends
5. **Export Options** - CSV, JSON, or interactive HTML reports
