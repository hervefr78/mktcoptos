# MARKETER APP - COMPREHENSIVE TECHNICAL SPECIFICATION

**Version:** 1.0
**Date:** 2025-01-14
**Status:** Draft

---

## TABLE OF CONTENTS

1. [System Overview](#1-system-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent System Architecture](#3-agent-system-architecture)
4. [Complete Application Workflows](#4-complete-application-workflows)
5. [Infrastructure Specifications](#5-infrastructure-specifications)
6. [Security & Compliance](#6-security--compliance)
7. [Database Schema](#7-database-schema)
8. [API Specifications](#8-api-specifications)
9. [UI/UX Specifications](#9-uiux-specifications)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Monitoring & Observability](#11-monitoring--observability)
12. [Performance Requirements](#12-performance-requirements)

---

## 1. SYSTEM OVERVIEW

### 1.1 Purpose

Marketer App is an AI-powered marketing content generation platform that enables marketers to create SEO-optimized content using multiple specialized AI agents. The platform supports both local (privacy-first) and cloud LLM processing, with a hybrid SaaS model.

### 1.2 Key Features

- **Multi-Agent Content Generation**: Specialized agents for SEO, writing, research, editing, and social media
- **Orchestrated Workflows**: LangGraph-powered workflow engine coordinating agent collaboration
- **RAG System**: ChromaDB-powered document retrieval for brand voice and context
- **Hybrid Deployment**: Local Mac app, cloud SaaS, or hybrid (SaaS + local LLM)
- **Multi-LLM Support**: Ollama (local), OpenAI, Anthropic Claude, Mistral AI
- **Privacy-First**: Optional local LLM processing for sensitive content
- **Team Collaboration**: Multi-user organizations with role-based access

### 1.3 Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL 16 (database)
- ChromaDB (vector store)
- Redis (cache + queue broker)
- Celery (async task processing)
- LangGraph (agent orchestration)
- SQLAlchemy (ORM)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Zustand (state management)
- shadcn/ui (component library)
- TanStack Query (data fetching)
- React Router v6 (routing)

**Infrastructure:**
- Docker + Docker Compose
- PostgreSQL (persistent storage)
- Redis (caching/message broker)
- Ollama (local LLM server)
- Nginx (reverse proxy)
- Kubernetes (production deployment)

**LLM Providers:**
- Ollama (llama3, mistral, phi-3)
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude Sonnet, Claude Opus)
- Mistral AI (Mistral Large, Mistral Small)

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Dashboard │  │Workflows │  │Documents │  │Settings  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                 │
│                    React + TypeScript + Vite                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS/WSS
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      BACKEND API (FastAPI)                      │
│                            │                                     │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │         API Router      │                                 │ │
│  │  ┌──────────┬──────────┬┼────────┬─────────┬──────────┐  │ │
│  │  │  Auth    │ Projects ││Workflow│Documents│  Admin   │  │ │
│  │  └──────────┴──────────┴┼────────┴─────────┴──────────┘  │ │
│  └─────────────────────────┼─────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │      AGENT SYSTEM       │                                 │ │
│  │                         │                                 │ │
│  │  ┌──────────────────────▼──────────────────────────────┐ │ │
│  │  │         Orchestrator Agent (LangGraph)             │ │ │
│  │  │                                                     │ │ │
│  │  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐│ │ │
│  │  │  │ SEO  │→ │Research│→│Writer│→│Editor│→│Social││ │ │
│  │  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘│ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                         │                                 │ │
│  │  ┌──────────────────────┼─────────────────────────────┐ │ │
│  │  │       LLM Router     │                             │ │ │
│  │  │         ┌────────────┼────────────┐                │ │ │
│  │  │         │  Mode: Cloud / Local    │                │ │ │
│  │  │         └────────────┬────────────┘                │ │ │
│  │  └──────────────────────┼─────────────────────────────┘ │ │
│  └─────────────────────────┼─────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────────┐ │
│  │              SUPPORTING SERVICES                          │ │
│  │  ┌──────────┬──────────┬──────────┬──────────┬─────────┐ │ │
│  │  │  RAG     │ Celery   │  Redis   │  Usage   │  Billing│ │ │
│  │  │(ChromaDB)│  Tasks   │  Cache   │ Tracking │ (Stripe)│ │ │
│  │  └──────────┴──────────┴──────────┴──────────┴─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼─────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│   PostgreSQL    │  │    ChromaDB     │  │     Redis       │
│   (Database)    │  │ (Vector Store)  │  │  (Cache/Queue)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      LLM PROVIDERS                              │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Ollama  │  │  OpenAI  │  │Anthropic │  │ Mistral  │      │
│  │ (Local)  │  │ (Cloud)  │  │ (Cloud)  │  │ (Cloud)  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment Models

#### Model 1: Local (Mac Desktop App)

```
┌─────────────────────────────────────────────────┐
│              MacBook (User's Machine)           │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Frontend (Browser: localhost:3000)     │  │
│  └──────────────────┬───────────────────────┘  │
│                     │                           │
│  ┌──────────────────▼───────────────────────┐  │
│  │  Backend API (localhost:8000)           │  │
│  └──────────────────┬───────────────────────┘  │
│                     │                           │
│  ┌──────────────────┼───────────────────────┐  │
│  │  Docker Compose  │                       │  │
│  │  ┌───────────────▼────────────────────┐  │  │
│  │  │ PostgreSQL │ ChromaDB │ Redis      │  │  │
│  │  └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Ollama (localhost:11434)               │  │
│  │  Models: llama3, mistral, phi-3         │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  Storage: ~/Library/Application Support/       │
│           MarketerApp/data/                     │
└─────────────────────────────────────────────────┘

Features:
✓ No internet required (after model download)
✓ Unlimited usage
✓ Full privacy
✓ No subscription
```

#### Model 2: Cloud SaaS

```
┌─────────────────────────────────────────────────┐
│              User's Browser                     │
│         https://app.marketer-app.com            │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS
                       │
┌──────────────────────▼──────────────────────────┐
│                  AWS/GCP Cloud                  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Load Balancer (ALB/GCLB)               │  │
│  └──────────────────┬───────────────────────┘  │
│                     │                           │
│  ┌──────────────────▼───────────────────────┐  │
│  │  Kubernetes Cluster                     │  │
│  │                                          │  │
│  │  ┌───────────┐  ┌───────────┐          │  │
│  │  │ Frontend  │  │  Backend  │          │  │
│  │  │  Pods     │  │   Pods    │          │  │
│  │  └───────────┘  └───────────┘          │  │
│  │                                          │  │
│  │  ┌───────────┐  ┌───────────┐          │  │
│  │  │  Worker   │  │  Agent    │          │  │
│  │  │  Pods     │  │  WS Pods  │          │  │
│  │  └───────────┘  └───────────┘          │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Managed Services                        │  │
│  │  ┌──────────┬──────────┬──────────┐     │  │
│  │  │   RDS    │ElastiCache│    S3    │     │  │
│  │  │PostgreSQL│   Redis   │ Storage  │     │  │
│  │  └──────────┴──────────┴──────────┘     │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ChromaDB: Self-hosted on K8s or Managed       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│          External Services                      │
│  OpenAI, Anthropic, Mistral (Cloud LLMs)       │
│  Stripe (Billing), Clerk (Auth)                │
└─────────────────────────────────────────────────┘

Features:
✓ Multi-tenant
✓ Team collaboration
✓ Cloud LLMs only
✓ Subscription-based
```

#### Model 3: Hybrid (SaaS + Local LLM)

```
┌─────────────────────────────────────────────────┐
│              User's Browser                     │
│         https://app.marketer-app.com            │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS
                       │
┌──────────────────────▼──────────────────────────┐
│                  Cloud SaaS                     │
│  (UI, Database, Orchestration, Storage)         │
│                                                 │
│  Backend handles:                               │
│  - User authentication                          │
│  - Project/campaign management                  │
│  - Workflow orchestration                       │
│  - Document storage (S3)                        │
│  - Vector store (ChromaDB)                      │
│  - Usage tracking & billing                     │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Agent WebSocket Server                  │  │
│  │  (Coordinates with customer agents)      │  │
│  └──────────────────┬───────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │ WSS (Secure WebSocket)
                      │ Encrypted Tunnel
┌─────────────────────▼───────────────────────────┐
│        Customer Infrastructure                  │
│        (On-Premises / Private Cloud)            │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Marketer Agent (Golang)                │  │
│  │  - Maintains connection to SaaS         │  │
│  │  - Receives LLM requests                │  │
│  │  - Processes locally                    │  │
│  │  - Streams results back                 │  │
│  └──────────────────┬───────────────────────┘  │
│                     │                           │
│  ┌──────────────────▼───────────────────────┐  │
│  │  Ollama (localhost:11434)               │  │
│  │  Models: llama3, mistral, custom        │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  Content NEVER leaves this environment          │
└─────────────────────────────────────────────────┘

Features:
✓ SaaS convenience
✓ Local LLM processing
✓ Privacy + compliance
✓ Enterprise pricing
```

---

## 3. AGENT SYSTEM ARCHITECTURE

### 3.1 Agent Overview

The system uses a **multi-agent architecture** with specialized agents coordinated by an orchestrator.

**Agent Types:**

1. **Orchestrator Agent** - Manages workflow and coordinates other agents
2. **SEO Research Agent** - Keyword research, SERP analysis, optimization
3. **Content Research Agent** - Information gathering from RAG and web
4. **Content Writer Agent** - Long-form content generation
5. **Editor Agent** - Quality review, refinement, brand consistency
6. **Social Media Agent** - Platform-specific content adaptation

### 3.2 Base Agent Architecture

```python
# backend/app/agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel

class AgentInput(BaseModel):
    """Standardized input for all agents."""
    prompt: str
    context: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class AgentOutput(BaseModel):
    """Standardized output from all agents."""
    content: str
    metadata: Dict[str, Any] = {}
    sources: List[str] = []
    confidence: float = 1.0
    tokens_used: int = 0
    duration_ms: int = 0

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        llm_router: 'LLMRouter',
        vector_store: Optional['ChromaRAGStore'] = None
    ):
        self.llm_router = llm_router
        self.vector_store = vector_store
        self.metrics = AgentMetrics(agent_name=self.name())

    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Execute the agent's main task."""
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Return the agent's unique name."""
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        """Return a description of what this agent does."""
        raise NotImplementedError

    @abstractmethod
    def required_capabilities(self) -> List[str]:
        """Return list of required LLM capabilities."""
        # e.g., ["chat", "streaming", "function_calling"]
        raise NotImplementedError

    async def _track_execution(self, func):
        """Decorator to track agent execution metrics."""
        start_time = time.time()
        try:
            result = await func
            self.metrics.record_success(time.time() - start_time)
            return result
        except Exception as e:
            self.metrics.record_failure(time.time() - start_time, str(e))
            raise

class AgentMetrics:
    """Tracks agent performance metrics."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.executions = 0
        self.successes = 0
        self.failures = 0
        self.total_duration = 0
        self.total_tokens = 0

    def record_success(self, duration: float):
        self.executions += 1
        self.successes += 1
        self.total_duration += duration

    def record_failure(self, duration: float, error: str):
        self.executions += 1
        self.failures += 1
        self.total_duration += duration
        logger.error(f"Agent {self.agent_name} failed: {error}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "executions": self.executions,
            "success_rate": self.successes / max(self.executions, 1),
            "avg_duration": self.total_duration / max(self.executions, 1),
            "total_tokens": self.total_tokens
        }
```

### 3.3 Specialized Agent Implementations

#### 3.3.1 SEO Research Agent

```python
# backend/app/agents/seo_research_agent.py
from typing import List, Dict
import asyncio

class SEOResearchAgent(BaseAgent):
    """Analyzes keywords and generates SEO recommendations."""

    def name(self) -> str:
        return "seo_research"

    def description(self) -> str:
        return "Analyzes keywords, search intent, and generates SEO optimization recommendations"

    def required_capabilities(self) -> List[str]:
        return ["chat", "json_output"]

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute SEO research workflow:
        1. Analyze primary and related keywords
        2. Determine search intent
        3. Suggest title, meta description, headings
        4. Recommend content structure
        """
        topic = input_data.context.get("topic", "")
        keywords = input_data.context.get("keywords", [])
        target_audience = input_data.context.get("target_audience", "")

        # Build prompt
        prompt = f"""
        You are an SEO expert. Analyze the following topic and keywords for content optimization.

        Topic: {topic}
        Keywords: {', '.join(keywords)}
        Target Audience: {target_audience}

        Provide SEO recommendations in the following JSON format:
        {{
            "primary_keyword": "string",
            "related_keywords": ["string"],
            "search_intent": "informational|transactional|navigational",
            "suggested_title": "string (50-60 chars)",
            "meta_description": "string (150-160 chars)",
            "heading_structure": {{
                "h1": "string",
                "h2": ["string"],
                "h3": ["string"]
            }},
            "content_outline": ["string"],
            "target_word_count": number,
            "optimization_tips": ["string"]
        }}
        """

        # Call LLM
        start_time = time.time()
        response = await self.llm_router.generate(
            prompt=prompt,
            model="gpt-4o-mini",  # Fast model for structured output
            response_format="json"
        )
        duration_ms = int((time.time() - start_time) * 1000)

        # Parse JSON
        seo_data = json.loads(response.content)

        return AgentOutput(
            content=json.dumps(seo_data, indent=2),
            metadata={
                "seo_recommendations": seo_data,
                "agent": self.name()
            },
            sources=[],
            confidence=0.9,
            tokens_used=response.tokens_used,
            duration_ms=duration_ms
        )

    async def analyze_keywords(self, keywords: List[str]) -> Dict:
        """Analyze keyword difficulty and search volume (mock)."""
        # In production, integrate with SEO APIs (SEMrush, Ahrefs, etc.)
        return {
            keyword: {
                "difficulty": random.randint(1, 100),
                "volume": random.randint(100, 10000),
                "cpc": round(random.uniform(0.5, 5.0), 2)
            }
            for keyword in keywords
        }
```

#### 3.3.2 Content Research Agent

```python
# backend/app/agents/research_agent.py
class ContentResearchAgent(BaseAgent):
    """Gathers information from RAG and web sources."""

    def name(self) -> str:
        return "content_research"

    def description(self) -> str:
        return "Retrieves relevant information from documents and performs web research"

    def required_capabilities(self) -> List[str]:
        return ["chat", "retrieval"]

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute research workflow:
        1. Query RAG system for relevant documents
        2. Extract key facts and data
        3. Identify gaps in information
        4. Optionally perform web research
        """
        topic = input_data.context.get("topic", "")
        project_id = input_data.context.get("project_id")
        seo_data = input_data.context.get("seo_data", {})

        # Query ChromaDB for relevant content
        if self.vector_store and project_id:
            search_queries = [
                topic,
                seo_data.get("primary_keyword", ""),
                *seo_data.get("related_keywords", [])[:3]
            ]

            all_results = []
            for query in search_queries:
                if query:
                    results = await self.vector_store.hybrid_search(
                        project_id=project_id,
                        query=query,
                        k=5
                    )
                    all_results.extend(results)

            # Deduplicate and rank
            unique_results = self._deduplicate_results(all_results)
            context_text = "\n\n".join([
                f"[Source: {r['metadata']['filename']}]\n{r['text']}"
                for r in unique_results[:10]
            ])
        else:
            context_text = ""

        # Build research prompt
        prompt = f"""
        You are a research assistant. Analyze the following information and extract key facts relevant to the topic.

        Topic: {topic}
        Keywords: {', '.join(seo_data.get('related_keywords', []))}

        Available Context:
        {context_text}

        Provide a structured summary:
        1. Key facts and statistics
        2. Important definitions or concepts
        3. Brand voice guidelines (if found)
        4. Relevant examples or case studies
        5. Information gaps that need external research

        Format as JSON with clear sections.
        """

        start_time = time.time()
        response = await self.llm_router.generate(
            prompt=prompt,
            model="claude-sonnet-3.5",  # Good at analysis
            response_format="json"
        )
        duration_ms = int((time.time() - start_time) * 1000)

        research_data = json.loads(response.content)

        # Track sources
        sources = [r['metadata']['filename'] for r in unique_results]

        return AgentOutput(
            content=json.dumps(research_data, indent=2),
            metadata={
                "research_findings": research_data,
                "context_used": len(unique_results),
                "agent": self.name()
            },
            sources=sources,
            confidence=0.85,
            tokens_used=response.tokens_used,
            duration_ms=duration_ms
        )

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate search results based on content similarity."""
        seen = set()
        unique = []
        for result in results:
            # Simple deduplication by ID
            doc_id = result.get('id')
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(result)
        return unique
```

#### 3.3.3 Content Writer Agent

```python
# backend/app/agents/content_writer_agent.py
class ContentWriterAgent(BaseAgent):
    """Generates long-form content based on research and SEO guidelines."""

    def name(self) -> str:
        return "content_writer"

    def description(self) -> str:
        return "Generates SEO-optimized long-form content following brand guidelines"

    def required_capabilities(self) -> List[str]:
        return ["chat", "long_context", "streaming"]

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute writing workflow:
        1. Review SEO recommendations and research findings
        2. Generate content outline
        3. Write full content following structure
        4. Incorporate keywords naturally
        5. Match brand voice
        """
        topic = input_data.context.get("topic", "")
        content_type = input_data.context.get("content_type", "blog")
        seo_data = input_data.context.get("seo_data", {})
        research_data = input_data.context.get("research_data", {})
        tone = input_data.context.get("tone", "professional")
        target_length = seo_data.get("target_word_count", 1500)

        # Build comprehensive writing prompt
        prompt = f"""
        You are an expert content writer. Create a {content_type} post on the following topic.

        Topic: {topic}
        Target Length: {target_length} words
        Tone: {tone}

        SEO Guidelines:
        - Primary Keyword: {seo_data.get('primary_keyword', '')}
        - Related Keywords: {', '.join(seo_data.get('related_keywords', []))}
        - Title: {seo_data.get('suggested_title', '')}
        - Meta Description: {seo_data.get('meta_description', '')}

        Heading Structure:
        {json.dumps(seo_data.get('heading_structure', {}), indent=2)}

        Content Outline:
        {chr(10).join(f"- {item}" for item in seo_data.get('content_outline', []))}

        Research Findings:
        {json.dumps(research_data, indent=2)}

        Instructions:
        1. Follow the heading structure exactly
        2. Incorporate keywords naturally (avoid keyword stuffing)
        3. Use the research findings to support claims with facts
        4. Write in a {tone} tone appropriate for the target audience
        5. Include engaging introduction and strong conclusion
        6. Use short paragraphs (3-4 sentences) for readability
        7. Add transitional phrases between sections
        8. Target approximately {target_length} words

        Write the complete article now:
        """

        start_time = time.time()
        response = await self.llm_router.generate(
            prompt=prompt,
            model="claude-opus-3",  # Best for long-form writing
            max_tokens=4096,
            temperature=0.7
        )
        duration_ms = int((time.time() - start_time) * 1000)

        content = response.content

        # Calculate word count
        word_count = len(content.split())

        return AgentOutput(
            content=content,
            metadata={
                "word_count": word_count,
                "content_type": content_type,
                "tone": tone,
                "seo_optimized": True,
                "agent": self.name()
            },
            sources=[],
            confidence=0.9,
            tokens_used=response.tokens_used,
            duration_ms=duration_ms
        )
```

#### 3.3.4 Editor Agent

```python
# backend/app/agents/editor_agent.py
class EditorAgent(BaseAgent):
    """Reviews and refines content for quality and brand consistency."""

    def name(self) -> str:
        return "editor"

    def description(self) -> str:
        return "Reviews content for quality, accuracy, grammar, and brand consistency"

    def required_capabilities(self) -> List[str]:
        return ["chat", "analysis"]

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute editing workflow:
        1. Review content for grammar and readability
        2. Check brand voice consistency
        3. Verify SEO optimization
        4. Suggest improvements
        5. Generate final polished version
        """
        draft_content = input_data.context.get("draft_content", "")
        seo_data = input_data.context.get("seo_data", {})
        brand_guidelines = input_data.context.get("brand_guidelines", "")

        # First pass: Analysis
        analysis_prompt = f"""
        You are a professional editor. Analyze the following draft content and provide feedback.

        Draft Content:
        {draft_content}

        SEO Requirements:
        - Primary Keyword: {seo_data.get('primary_keyword', '')} (should appear naturally)
        - Related Keywords: {', '.join(seo_data.get('related_keywords', []))}

        Brand Guidelines:
        {brand_guidelines}

        Analyze the content on these dimensions:
        1. Grammar and spelling errors
        2. Readability (Flesch-Kincaid score)
        3. SEO optimization (keyword usage, density)
        4. Brand voice consistency
        5. Content structure and flow
        6. Factual accuracy concerns
        7. Engagement level

        Provide analysis in JSON format with scores (0-10) and specific suggestions.
        """

        analysis_response = await self.llm_router.generate(
            prompt=analysis_prompt,
            model="gpt-4o",
            response_format="json"
        )

        analysis = json.loads(analysis_response.content)
        quality_score = analysis.get("overall_score", 7)

        # Decide if refinement is needed
        if quality_score < 8:
            # Second pass: Refinement
            refinement_prompt = f"""
            You are a professional editor. Improve the following draft based on the analysis.

            Draft Content:
            {draft_content}

            Analysis and Suggestions:
            {json.dumps(analysis, indent=2)}

            Instructions:
            1. Fix all grammar and spelling errors
            2. Improve readability while maintaining meaning
            3. Ensure keywords are used naturally
            4. Match the brand voice
            5. Enhance engagement with better hooks and transitions
            6. Keep the same structure and key points

            Provide the refined version:
            """

            refinement_response = await self.llm_router.generate(
                prompt=refinement_prompt,
                model="claude-sonnet-3.5",
                temperature=0.3  # Lower temperature for editing
            )

            final_content = refinement_response.content
            tokens_used = analysis_response.tokens_used + refinement_response.tokens_used
        else:
            # Content is good enough
            final_content = draft_content
            tokens_used = analysis_response.tokens_used

        duration_ms = int((time.time() - start_time) * 1000)

        return AgentOutput(
            content=final_content,
            metadata={
                "quality_score": quality_score,
                "analysis": analysis,
                "refinement_applied": quality_score < 8,
                "agent": self.name()
            },
            sources=[],
            confidence=quality_score / 10,
            tokens_used=tokens_used,
            duration_ms=duration_ms
        )
```

#### 3.3.5 Social Media Agent

```python
# backend/app/agents/social_media_agent.py
class SocialMediaAgent(BaseAgent):
    """Adapts content for different social media platforms."""

    def name(self) -> str:
        return "social_media"

    def description(self) -> str:
        return "Creates platform-specific social media content variants"

    def required_capabilities(self) -> List[str]:
        return ["chat"]

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute social media adaptation workflow:
        1. Analyze original content
        2. Create variants for each platform
        3. Optimize for platform-specific best practices
        """
        original_content = input_data.context.get("original_content", "")
        platforms = input_data.context.get("platforms", ["linkedin", "twitter", "facebook"])
        topic = input_data.context.get("topic", "")

        variants = {}

        for platform in platforms:
            platform_spec = self._get_platform_specs(platform)

            prompt = f"""
            You are a social media expert. Adapt the following content for {platform.upper()}.

            Original Content:
            {original_content[:1000]}...  # First 1000 chars for context

            Platform: {platform}
            Specifications:
            - Character Limit: {platform_spec['char_limit']}
            - Optimal Length: {platform_spec['optimal_length']}
            - Tone: {platform_spec['tone']}
            - Best Practices: {', '.join(platform_spec['best_practices'])}

            Create an engaging post for {platform} that:
            1. Captures the main message
            2. Uses appropriate tone and style
            3. Includes relevant hashtags (if applicable)
            4. Adds a call-to-action
            5. Stays within character limits

            Provide the post only, no explanations.
            """

            response = await self.llm_router.generate(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.8  # More creative for social
            )

            variants[platform] = {
                "content": response.content,
                "char_count": len(response.content),
                "hashtags": self._extract_hashtags(response.content)
            }

        duration_ms = int((time.time() - start_time) * 1000)

        return AgentOutput(
            content=json.dumps(variants, indent=2),
            metadata={
                "platforms": platforms,
                "variants": variants,
                "agent": self.name()
            },
            sources=[],
            confidence=0.85,
            tokens_used=sum(v.get('tokens', 0) for v in variants.values()),
            duration_ms=duration_ms
        )

    def _get_platform_specs(self, platform: str) -> Dict:
        """Return platform-specific specifications."""
        specs = {
            "linkedin": {
                "char_limit": 3000,
                "optimal_length": 150,
                "tone": "professional",
                "best_practices": [
                    "Use 3-5 hashtags",
                    "Ask questions",
                    "Share insights",
                    "Include line breaks"
                ]
            },
            "twitter": {
                "char_limit": 280,
                "optimal_length": 240,
                "tone": "conversational",
                "best_practices": [
                    "Use 1-2 hashtags",
                    "Include emojis",
                    "Create threads for longer content",
                    "Add media"
                ]
            },
            "facebook": {
                "char_limit": 63206,
                "optimal_length": 250,
                "tone": "friendly",
                "best_practices": [
                    "Use emojis",
                    "Ask questions",
                    "Include images",
                    "Create engagement"
                ]
            },
            "instagram": {
                "char_limit": 2200,
                "optimal_length": 150,
                "tone": "casual",
                "best_practices": [
                    "Use 10-15 hashtags",
                    "Lots of emojis",
                    "Short paragraphs",
                    "Strong visual hook"
                ]
            }
        }
        return specs.get(platform, specs["linkedin"])

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        import re
        return re.findall(r'#\w+', content)
```

### 3.4 Orchestrator Agent (LangGraph)

```python
# backend/app/agents/orchestrator.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage
import operator

class WorkflowState(TypedDict):
    """State passed between agents in the workflow."""
    # Input
    activity_id: int
    topic: str
    keywords: List[str]
    content_type: str
    tone: str
    target_audience: str
    project_id: int

    # Agent outputs
    seo_data: Dict[str, Any]
    research_data: Dict[str, Any]
    draft_content: str
    edited_content: str
    social_variants: Dict[str, Any]

    # Metadata
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_step: str
    quality_score: float
    refinement_count: int
    error: Optional[str]

class ContentOrchestrator:
    """Orchestrates the multi-agent content generation workflow."""

    def __init__(
        self,
        seo_agent: SEOResearchAgent,
        research_agent: ContentResearchAgent,
        writer_agent: ContentWriterAgent,
        editor_agent: EditorAgent,
        social_agent: SocialMediaAgent
    ):
        self.seo_agent = seo_agent
        self.research_agent = research_agent
        self.writer_agent = writer_agent
        self.editor_agent = editor_agent
        self.social_agent = social_agent

        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)

        # Add nodes (agent execution functions)
        workflow.add_node("seo_research", self._run_seo_research)
        workflow.add_node("content_research", self._run_content_research)
        workflow.add_node("content_writer", self._run_content_writer)
        workflow.add_node("editor", self._run_editor)
        workflow.add_node("social_media", self._run_social_media)
        workflow.add_node("finalize", self._finalize)

        # Define workflow edges
        workflow.set_entry_point("seo_research")

        workflow.add_edge("seo_research", "content_research")
        workflow.add_edge("content_research", "content_writer")
        workflow.add_edge("content_writer", "editor")

        # Conditional edge: editor can loop back or proceed
        workflow.add_conditional_edges(
            "editor",
            self._should_refine,
            {
                "refine": "content_writer",  # Loop back for refinement
                "social": "social_media",     # Proceed to social variants
                "error": END                  # Stop on error
            }
        )

        workflow.add_edge("social_media", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _run_seo_research(self, state: WorkflowState) -> WorkflowState:
        """Execute SEO research agent."""
        try:
            input_data = AgentInput(
                prompt=f"Analyze SEO for: {state['topic']}",
                context={
                    "topic": state["topic"],
                    "keywords": state["keywords"],
                    "target_audience": state["target_audience"]
                }
            )

            output = await self.seo_agent.run(input_data)
            state["seo_data"] = output.metadata["seo_recommendations"]
            state["current_step"] = "seo_research_complete"

            # Update activity in database
            await self._update_activity_progress(
                state["activity_id"],
                step="seo_research",
                data=state["seo_data"]
            )

        except Exception as e:
            state["error"] = f"SEO research failed: {str(e)}"
            logger.error(f"SEO agent error: {e}")

        return state

    async def _run_content_research(self, state: WorkflowState) -> WorkflowState:
        """Execute content research agent."""
        try:
            input_data = AgentInput(
                prompt=f"Research: {state['topic']}",
                context={
                    "topic": state["topic"],
                    "project_id": state["project_id"],
                    "seo_data": state["seo_data"]
                }
            )

            output = await self.research_agent.run(input_data)
            state["research_data"] = output.metadata["research_findings"]
            state["current_step"] = "research_complete"

            await self._update_activity_progress(
                state["activity_id"],
                step="research",
                data=state["research_data"]
            )

        except Exception as e:
            state["error"] = f"Research failed: {str(e)}"
            logger.error(f"Research agent error: {e}")

        return state

    async def _run_content_writer(self, state: WorkflowState) -> WorkflowState:
        """Execute content writer agent."""
        try:
            input_data = AgentInput(
                prompt=f"Write about: {state['topic']}",
                context={
                    "topic": state["topic"],
                    "content_type": state["content_type"],
                    "tone": state["tone"],
                    "seo_data": state["seo_data"],
                    "research_data": state["research_data"]
                }
            )

            output = await self.writer_agent.run(input_data)
            state["draft_content"] = output.content
            state["current_step"] = "draft_complete"

            await self._update_activity_progress(
                state["activity_id"],
                step="writing",
                data={"word_count": output.metadata["word_count"]}
            )

        except Exception as e:
            state["error"] = f"Writing failed: {str(e)}"
            logger.error(f"Writer agent error: {e}")

        return state

    async def _run_editor(self, state: WorkflowState) -> WorkflowState:
        """Execute editor agent."""
        try:
            # Get brand guidelines from RAG if available
            brand_guidelines = ""
            if state["project_id"]:
                # Query for brand guide documents
                results = await self.research_agent.vector_store.hybrid_search(
                    project_id=state["project_id"],
                    query="brand voice guidelines tone style",
                    k=3
                )
                brand_guidelines = "\n".join([r["text"] for r in results])

            input_data = AgentInput(
                prompt="Edit and refine content",
                context={
                    "draft_content": state["draft_content"],
                    "seo_data": state["seo_data"],
                    "brand_guidelines": brand_guidelines
                }
            )

            output = await self.editor_agent.run(input_data)
            state["edited_content"] = output.content
            state["quality_score"] = output.metadata["quality_score"]
            state["refinement_count"] = state.get("refinement_count", 0) + 1
            state["current_step"] = "editing_complete"

            await self._update_activity_progress(
                state["activity_id"],
                step="editing",
                data={
                    "quality_score": state["quality_score"],
                    "refinement_count": state["refinement_count"]
                }
            )

        except Exception as e:
            state["error"] = f"Editing failed: {str(e)}"
            logger.error(f"Editor agent error: {e}")

        return state

    def _should_refine(self, state: WorkflowState) -> Literal["refine", "social", "error"]:
        """Decide if content needs refinement."""
        if state.get("error"):
            return "error"

        quality_score = state.get("quality_score", 10)
        refinement_count = state.get("refinement_count", 0)

        # Refine if quality < 8 and haven't refined more than 2 times
        if quality_score < 8 and refinement_count < 2:
            return "refine"
        else:
            return "social"

    async def _run_social_media(self, state: WorkflowState) -> WorkflowState:
        """Execute social media agent."""
        try:
            input_data = AgentInput(
                prompt="Create social media variants",
                context={
                    "original_content": state["edited_content"],
                    "topic": state["topic"],
                    "platforms": ["linkedin", "twitter", "facebook"]
                }
            )

            output = await self.social_agent.run(input_data)
            state["social_variants"] = output.metadata["variants"]
            state["current_step"] = "social_complete"

            await self._update_activity_progress(
                state["activity_id"],
                step="social_media",
                data=state["social_variants"]
            )

        except Exception as e:
            state["error"] = f"Social media adaptation failed: {str(e)}"
            logger.error(f"Social agent error: {e}")

        return state

    async def _finalize(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow and save results."""
        try:
            # Save final content to database
            activity = await db.query(Activity).get(state["activity_id"])
            activity.content = {
                "final_content": state["edited_content"],
                "seo_data": state["seo_data"],
                "research_sources": state["research_data"].get("sources", []),
                "social_variants": state["social_variants"],
                "metadata": {
                    "quality_score": state["quality_score"],
                    "refinement_count": state["refinement_count"],
                    "word_count": len(state["edited_content"].split())
                }
            }
            activity.status = "completed"
            activity.updated_at = datetime.now()
            await db.commit()

            state["current_step"] = "complete"

        except Exception as e:
            state["error"] = f"Finalization failed: {str(e)}"
            logger.error(f"Finalization error: {e}")

        return state

    async def _update_activity_progress(
        self,
        activity_id: int,
        step: str,
        data: Dict[str, Any]
    ):
        """Update activity progress in real-time (for UI updates)."""
        # Publish to Redis for SSE streaming
        await redis_client.publish(
            f"activity:{activity_id}:progress",
            json.dumps({
                "step": step,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        )

    async def execute(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute the workflow and return final state."""
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state

    async def execute_streaming(self, initial_state: WorkflowState):
        """Execute workflow with streaming updates for UI."""
        async for state in self.workflow.astream(initial_state):
            yield state
```

### 3.5 Agent Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTENT GENERATION WORKFLOW                 │
└─────────────────────────────────────────────────────────────────┘

User Request
     │
     ▼
┌─────────────────────┐
│   Orchestrator      │
│   (LangGraph)       │
└──────────┬──────────┘
           │
           ├──────────────────────────────────────────────────┐
           │                                                  │
           ▼                                                  │
┌──────────────────────┐                                     │
│  SEO Research Agent  │                                     │
│  - Analyze keywords  │                                     │
│  - Determine intent  │                                     │
│  - Suggest structure │                                     │
└──────────┬───────────┘                                     │
           │ seo_data                                        │
           ▼                                                  │
┌──────────────────────┐                                     │
│ Content Research     │                                     │
│ Agent                │                                     │
│  - Query ChromaDB    │                                     │
│  - Extract facts     │                                     │
│  - Gather context    │                                     │
└──────────┬───────────┘                                     │
           │ research_data                                   │
           ▼                                                  │
┌──────────────────────┐                                     │
│ Content Writer Agent │                                     │
│  - Generate content  │                                     │
│  - Follow structure  │                                     │
│  - Use keywords      │ ◄───────┐                          │
└──────────┬───────────┘          │                          │
           │ draft_content        │                          │
           ▼                      │                          │
┌──────────────────────┐          │                          │
│   Editor Agent       │          │ refine                   │
│  - Review quality    │          │ (if score < 8)           │
│  - Check grammar     │ ─────────┘                          │
│  - Refine content    │                                     │
└──────────┬───────────┘                                     │
           │ edited_content                                  │
           │ (if score >= 8)                                 │
           ▼                                                  │
┌──────────────────────┐                                     │
│ Social Media Agent   │                                     │
│  - Create LinkedIn   │                                     │
│  - Create Twitter    │                                     │
│  - Create Facebook   │                                     │
└──────────┬───────────┘                                     │
           │ social_variants                                 │
           ▼                                                  │
┌──────────────────────┐                                     │
│   Finalize           │                                     │
│  - Save to DB        │                                     │
│  - Notify user       │                                     │
└──────────┬───────────┘                                     │
           │                                                  │
           └──────────────────────────────────────────────────┘
           │
           ▼
    Complete ✓
```

### 3.6 Agent Communication Protocol

All agents communicate using standardized input/output:

```python
# Request
{
    "agent": "content_writer",
    "input": {
        "prompt": "Write about AI in Marketing",
        "context": {
            "topic": "AI in Marketing",
            "keywords": ["AI", "automation", "personalization"],
            "seo_data": {...},
            "research_data": {...}
        },
        "metadata": {
            "activity_id": 123,
            "user_id": 456
        }
    }
}

# Response
{
    "agent": "content_writer",
    "output": {
        "content": "# AI in Marketing: Transforming...",
        "metadata": {
            "word_count": 1543,
            "content_type": "blog",
            "seo_optimized": true
        },
        "sources": [],
        "confidence": 0.9,
        "tokens_used": 3200,
        "duration_ms": 8500
    },
    "status": "success"
}
```

---

## 4. COMPLETE APPLICATION WORKFLOWS

### 4.1 User Registration & Onboarding (SaaS)

```
┌──────────────┐
│  User visits │
│  website     │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Sign up with email   │ ──────► Clerk Authentication
│ or Social (Google)   │
└──────┬───────────────┘
       │ authenticated
       ▼
┌──────────────────────┐
│ Create Organization  │
│ - Company name       │
│ - Industry           │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Select Plan          │
│ - Free (trial)       │
│ - Pro ($49/mo)       │
│ - Enterprise         │
└──────┬───────────────┘
       │ if Pro/Enterprise
       ▼
┌──────────────────────┐
│ Payment (Stripe)     │
│ - Card details       │
│ - Billing info       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Onboarding Wizard    │
│ 1. Create first      │
│    project           │
│ 2. Upload brand docs │
│ 3. Configure LLMs    │
│ 4. Invite team       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Dashboard            │
└──────────────────────┘
```

### 4.2 Content Creation Workflow (Main Use Case)

```
┌──────────────────────────────────────────────────┐
│ 1. USER INITIATES CONTENT CREATION               │
└──────────────────────────────────────────────────┘
User clicks "New Activity" → Activity Wizard opens

Step 1: Select Project/Campaign
├─ Choose existing project or create new
└─ Choose existing campaign or create new

Step 2: Define Activity
├─ Content Type: Blog, LinkedIn, Twitter, Web Page
├─ Topic: "AI in Marketing Automation"
├─ Keywords: ["AI", "marketing automation", "personalization"]
├─ Target Audience: "Marketing managers at B2B companies"
├─ Tone: Professional / Casual / Technical
└─ Target Length: 1500 words

Step 3: Additional Options
├─ Reference Documents: Select from uploaded docs
├─ Tone Reference: Link to example content
└─ SEO Priority: High / Medium / Low

User clicks "Generate Content" ──────► POST /api/workflows/execute

┌──────────────────────────────────────────────────┐
│ 2. BACKEND WORKFLOW ORCHESTRATION                │
└──────────────────────────────────────────────────┘

API Endpoint: POST /api/workflows/execute
Request Body:
{
    "activity_id": 789,
    "project_id": 123,
    "topic": "AI in Marketing Automation",
    "keywords": ["AI", "marketing automation"],
    "content_type": "blog",
    "tone": "professional",
    "target_audience": "Marketing managers"
}

Backend Flow:
1. Validate request
2. Check user quotas (requests/day, credits)
3. Create workflow task (Celery)
4. Return task_id to frontend
5. Initiate SSE stream for real-time updates

┌──────────────────────────────────────────────────┐
│ 3. AGENT ORCHESTRATION (Celery Task)            │
└──────────────────────────────────────────────────┘

@celery_app.task
async def execute_content_workflow(activity_id: int, params: dict):
    orchestrator = ContentOrchestrator(
        seo_agent=seo_agent,
        research_agent=research_agent,
        writer_agent=writer_agent,
        editor_agent=editor_agent,
        social_agent=social_agent
    )

    initial_state = WorkflowState(
        activity_id=activity_id,
        topic=params["topic"],
        keywords=params["keywords"],
        content_type=params["content_type"],
        tone=params["tone"],
        target_audience=params["target_audience"],
        project_id=params["project_id"],
        messages=[],
        current_step="initialized",
        quality_score=0.0,
        refinement_count=0,
        error=None
    )

    # Execute workflow with streaming
    async for state in orchestrator.execute_streaming(initial_state):
        # Publish progress to Redis for SSE
        await redis_client.publish(
            f"activity:{activity_id}:progress",
            json.dumps({
                "step": state["current_step"],
                "progress": calculate_progress(state),
                "timestamp": datetime.now().isoformat()
            })
        )

    return state

Agent Execution Steps:

Step 1: SEO Research Agent (15-30 seconds)
├─ Analyze keywords
├─ Generate title, meta description
├─ Create heading structure
└─ Publish update: "SEO analysis complete" (20%)

Step 2: Content Research Agent (20-40 seconds)
├─ Query ChromaDB for relevant documents
├─ Extract key facts and data
├─ Identify information gaps
└─ Publish update: "Research complete" (40%)

Step 3: Content Writer Agent (30-60 seconds)
├─ Generate full content based on research
├─ Follow SEO structure
├─ Incorporate keywords naturally
└─ Publish update: "Draft complete" (60%)

Step 4: Editor Agent (20-40 seconds)
├─ Analyze draft quality
├─ Check grammar and readability
├─ Refine if quality_score < 8
└─ Publish update: "Editing complete" (80%)

Step 5: Social Media Agent (15-30 seconds)
├─ Create LinkedIn variant
├─ Create Twitter variant
├─ Create Facebook variant
└─ Publish update: "Social variants ready" (95%)

Step 6: Finalize (5 seconds)
├─ Save all content to database
├─ Update activity status to "completed"
└─ Publish update: "Complete" (100%)

┌──────────────────────────────────────────────────┐
│ 4. FRONTEND REAL-TIME UPDATES (SSE)             │
└──────────────────────────────────────────────────┘

// Frontend connects to SSE endpoint
const eventSource = new EventSource(
    `/api/activities/${activityId}/stream`
);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Update UI
    setCurrentStep(data.step);
    setProgress(data.progress);

    // Display step-specific data
    if (data.step === "seo_research_complete") {
        displaySEORecommendations(data.seo_data);
    } else if (data.step === "draft_complete") {
        displayDraftPreview(data.draft_content);
    } else if (data.step === "complete") {
        showFinalContent(data.final_content);
        eventSource.close();
    }
};

UI Updates:
├─ Progress bar: 0% → 20% → 40% → 60% → 80% → 95% → 100%
├─ Status text: "Analyzing SEO..." → "Researching..." → "Writing..." → "Editing..." → "Creating social variants..." → "Complete!"
├─ Preview panel: Shows draft as it becomes available
└─ Completion: Show final content with edit options

┌──────────────────────────────────────────────────┐
│ 5. USER REVIEWS & EDITS                          │
└──────────────────────────────────────────────────┘

Content Ready Screen:
├─ Final Content (rich text editor)
├─ SEO Score & Recommendations
├─ Social Media Variants (tabs)
├─ Actions:
│   ├─ Edit Content (opens editor)
│   ├─ Regenerate (restart workflow)
│   ├─ Download (PDF, HTML, Markdown)
│   ├─ Publish to CMS
│   └─ Share on Social Media

User can:
1. Edit content directly in rich text editor
2. Accept changes → Save to database
3. Download in multiple formats
4. Export to WordPress, LinkedIn, etc.

┌──────────────────────────────────────────────────┐
│ 6. COMPLETION & ANALYTICS                        │
└──────────────────────────────────────────────────┘

Activity Saved:
├─ Activity record in database
├─ Content stored with metadata
├─ Usage tracked (tokens, cost)
├─ Analytics updated

User Dashboard Updated:
├─ Recent Activities list
├─ Project statistics
└─ Usage metrics (tokens, credits)
```

### 4.3 Document Upload & RAG Indexing

```
User uploads document (PDF, DOCX, TXT)
     │
     ▼
POST /api/documents (multipart/form-data)
     │
     ├─ Validate file (size, type)
     ├─ Check storage quota
     ├─ Generate unique ID
     └─ Save to storage
         ├─ Local: /data/rag_docs/{org_id}/{doc_id}.pdf
         └─ SaaS: S3 s3://bucket/orgs/{org_id}/docs/{doc_id}.pdf
     │
     ▼
Create Document record in database
     │
     └─ status: "pending"
     │
     ▼
Queue processing task (Celery)
     │
     ▼
@celery_app.task
async def process_document(document_id: int):
     │
     ├─ 1. Extract text
     │    ├─ PDF: PyPDF2 or pdfminer
     │    ├─ DOCX: python-docx
     │    └─ TXT: direct read
     │
     ├─ 2. Semantic chunking
     │    ├─ Split into logical sections
     │    ├─ Maintain context
     │    └─ Target 512 tokens per chunk
     │
     ├─ 3. Generate embeddings
     │    └─ SentenceTransformer: all-MiniLM-L6-v2
     │
     ├─ 4. Index in ChromaDB
     │    └─ Collection: project_{project_id}
     │         ├─ documents: [chunks]
     │         ├─ metadatas: [filename, page, section]
     │         └─ ids: [doc_{id}_chunk_{n}]
     │
     ├─ 5. Update document status
     │    └─ status: "processed"
     │
     └─ 6. Notify user (WebSocket or email)

User sees:
├─ Document list updated
├─ Status: "Processed" with checkmark
└─ Can now use document in workflows
```

### 4.5 Team Collaboration Workflow (SaaS)

```
Admin User Actions:

1. Invite Team Member
POST /api/organizations/{org_id}/invite
{
    "email": "colleague@company.com",
    "role": "member"  // owner, admin, member, viewer
}
     │
     ├─ Create invitation record
     ├─ Send invitation email
     └─ Set expiration (7 days)

2. New User Accepts Invitation
GET /invite/{token}
     │
     ├─ Validate token
     ├─ Create/link user account
     ├─ Add to organization
     └─ Set role and permissions

3. Collaborative Workflows
     │
     ├─ Member A: Creates project
     │    └─ Sets sharing: "Team" or "Private"
     │
     ├─ Member B: Views shared projects
     │    └─ Can create activities within projects
     │
     ├─ Member C: Reviews content
     │    └─ Adds comments or suggestions
     │
     └─ Admin: Manages team access
          ├─ Change roles
          ├─ Remove members
          └─ View activity logs

Permissions Matrix:
├─ Viewer: Read-only access
├─ Member: Create, edit own content
├─ Admin: Manage projects, invite users
└─ Owner: Full control, billing access
```

---

## 5. INFRASTRUCTURE SPECIFICATIONS

### 5.1 Local Deployment (Mac)

**Target Platform:** macOS 12+ (Intel & Apple Silicon)

**Architecture:**
```
~/Library/Application Support/MarketerApp/
├─ data/
│  ├─ postgres/          # PostgreSQL data directory
│  ├─ chromadb/          # ChromaDB persistent storage
│  ├─ redis/             # Redis dump
│  └─ uploads/           # User-uploaded files
├─ logs/
│  ├─ backend.log
│  ├─ celery.log
│  └─ ollama.log
└─ config/
   └─ settings.yaml      # User preferences
```

**Docker Compose Configuration:**

```yaml
# docker-compose.local.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: marketer
      POSTGRES_USER: marketer
      POSTGRES_PASSWORD: marketer_local
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U marketer"]
      interval: 10s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chromadb:latest
    environment:
      - ANONYMIZED_TELEMETRY=False
      - ALLOW_RESET=True
    volumes:
      - ./data/chromadb:/chroma/chroma
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - ./data/redis:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    # Pre-pull models on first run
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        ollama serve &
        sleep 10
        ollama pull llama3
        ollama pull mistral
        wait

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.local
    environment:
      - DEPLOYMENT_MODE=local
      - DATABASE_URL=postgresql://marketer:marketer_local@postgres:5432/marketer
      - REDIS_URL=redis://redis:6379/0
      - CHROMADB_HOST=chromadb:8000
      - OLLAMA_HOST=http://ollama:11434
      - USE_CLOUD=false
      - ENABLE_MULTI_TENANCY=false
      - ENABLE_BILLING=false
      - FILE_STORAGE=local
    volumes:
      - ./backend:/app
      - ./data/uploads:/data/uploads
      - ./logs:/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chromadb:
        condition: service_started
      ollama:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.local
    environment:
      - DEPLOYMENT_MODE=local
      - DATABASE_URL=postgresql://marketer:marketer_local@postgres:5432/marketer
      - REDIS_URL=redis://redis:6379/0
      - CHROMADB_HOST=chromadb:8000
      - OLLAMA_HOST=http://ollama:11434
    volumes:
      - ./backend:/app
      - ./data/uploads:/data/uploads
      - ./logs:/logs
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks worker --loglevel=info --logfile=/logs/celery.log

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.local
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_DEPLOYMENT_MODE=local
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    depends_on:
      - backend
    command: npm run dev -- --host 0.0.0.0

volumes:
  ollama_data:

networks:
  default:
    name: marketer_local
```

**System Requirements:**
- **RAM:** 16 GB minimum (8 GB for Ollama, 8 GB for rest)
- **Storage:** 50 GB free (20 GB for models, 30 GB for data)
- **CPU:** Multi-core (M1/M2 recommended for Ollama)
- **OS:** macOS 12+ (Monterey or later)

**Installation Script:**

```bash
#!/bin/bash
# install-local.sh

echo "Installing Marketer App (Local Mode)..."

# Check system requirements
echo "Checking system requirements..."
AVAILABLE_RAM=$(sysctl -n hw.memsize | awk '{print $0/1024/1024/1024}')
if (( $(echo "$AVAILABLE_RAM < 16" | bc -l) )); then
    echo "Warning: Less than 16 GB RAM detected. Performance may be affected."
fi

# Install Docker Desktop if not present
if ! command -v docker &> /dev/null; then
    echo "Docker Desktop not found. Please install from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Create data directories
mkdir -p ~/Library/Application\ Support/MarketerApp/{data/{postgres,chromadb,redis,uploads},logs,config}

# Clone repository (or extract from package)
git clone https://github.com/yourorg/marketer-app.git /tmp/marketer-app
cd /tmp/marketer-app

# Copy docker-compose for local
cp docker-compose.local.yml ~/Library/Application\ Support/MarketerApp/docker-compose.yml

# Start services
cd ~/Library/Application\ Support/MarketerApp
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create default admin user
docker-compose exec backend python -m app.scripts.create_admin

echo "✓ Installation complete!"
echo "Open http://localhost:3000 in your browser"
echo "Default credentials: admin / admin"
```

### 5.2 Cloud SaaS Deployment

**Platform:** AWS (recommended) or GCP

**Kubernetes Architecture:**

```yaml
# kubernetes/production/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: marketer-app-prod

---
# kubernetes/production/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: marketer-app-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
        version: v1
    spec:
      containers:
      - name: backend
        image: yourregistry/marketer-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEPLOYMENT_MODE
          value: "saas"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: CHROMADB_HOST
          value: "chromadb-service:8000"
        - name: USE_CLOUD
          value: "true"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-credentials
              key: openai
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-credentials
              key: anthropic
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
# kubernetes/production/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: marketer-app-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
        version: v1
    spec:
      containers:
      - name: frontend
        image: yourregistry/marketer-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: VITE_API_URL
          value: "https://api.marketer-app.com"
        - name: VITE_DEPLOYMENT_MODE
          value: "saas"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
# kubernetes/production/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: marketer-app-prod
spec:
  replicas: 5  # Scale based on load
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
        version: v1
    spec:
      containers:
      - name: worker
        image: yourregistry/marketer-backend:latest
        command: ["celery", "-A", "app.tasks", "worker", "--loglevel=info", "--concurrency=4"]
        env:
        - name: DEPLOYMENT_MODE
          value: "saas"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"

---
# kubernetes/production/chromadb-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: chromadb
  namespace: marketer-app-prod
spec:
  serviceName: chromadb
  replicas: 1
  selector:
    matchLabels:
      app: chromadb
  template:
    metadata:
      labels:
        app: chromadb
    spec:
      containers:
      - name: chromadb
        image: chromadb/chromadb:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: data
          mountPath: /chroma/chroma
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "8Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "gp3"
      resources:
        requests:
          storage: 100Gi

---
# kubernetes/production/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: marketer-app-prod
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: marketer-app-prod
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: chromadb-service
  namespace: marketer-app-prod
spec:
  selector:
    app: chromadb
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
# kubernetes/production/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
  namespace: marketer-app-prod
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.marketer-app.com
    - api.marketer-app.com
    secretName: marketer-tls
  rules:
  - host: app.marketer-app.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
  - host: api.marketer-app.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000

---
# kubernetes/production/hpa.yaml (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: marketer-app-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-hpa
  namespace: marketer-app-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker
  minReplicas: 5
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
```

**Managed Services (AWS):**

```yaml
# terraform/main.tf
resource "aws_db_instance" "postgres" {
  identifier = "marketer-app-prod"
  engine     = "postgres"
  engine_version = "16.1"

  instance_class = "db.r6g.xlarge"  # 4 vCPU, 32 GB RAM

  allocated_storage     = 100
  max_allocated_storage = 1000  # Auto-scaling
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "marketer"
  username = var.db_username
  password = var.db_password

  multi_az               = true  # High availability
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Environment = "production"
    Application = "marketer-app"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "marketer-app-prod"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.r6g.large"  # 2 vCPU, 13.07 GB RAM
  num_cache_nodes      = 2
  parameter_group_name = "default.redis7"

  subnet_group_name = aws_elasticache_subnet_group.redis.name

  tags = {
    Environment = "production"
    Application = "marketer-app"
  }
}

resource "aws_s3_bucket" "storage" {
  bucket = "marketer-app-prod-storage"

  tags = {
    Environment = "production"
    Application = "marketer-app"
  }
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

**Infrastructure Costs (AWS):**

| Component | Specs | Monthly Cost |
|-----------|-------|--------------|
| EKS Cluster | Control plane | $73 |
| EC2 Nodes | 3x c5.2xlarge (8 vCPU, 16GB) | $306 |
| RDS PostgreSQL | db.r6g.xlarge (Multi-AZ) | $486 |
| ElastiCache Redis | cache.r6g.large x2 | $218 |
| S3 Storage | 500 GB | $12 |
| Data Transfer | 1 TB/month | $90 |
| Load Balancer | ALB | $22 |
| CloudWatch | Logs + Metrics | $30 |
| **Total** | | **~$1,237/month** |

*Scales to ~1,000 users*

### 5.3 Hybrid Deployment (Agent-based)

**Customer Infrastructure:**

```yaml
# docker-compose.agent.yml (Customer runs this)
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped

  marketer-agent:
    image: marketer-app/agent:latest
    environment:
      - AGENT_API_KEY=${AGENT_API_KEY}
      - SAAS_URL=wss://api.marketer-app.com
      - OLLAMA_HOST=http://ollama:11434
      - AGENT_NAME=production
    depends_on:
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/app/agent", "health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama_data:
```

**Agent Installation:**

```bash
#!/bin/bash
# install-agent.sh

echo "Installing Marketer Agent..."

# Detect OS
OS=$(uname -s)
if [ "$OS" != "Linux" ] && [ "$OS" != "Darwin" ]; then
    echo "Unsupported OS: $OS"
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# Create agent directory
mkdir -p /opt/marketer-agent
cd /opt/marketer-agent

# Download docker-compose.yml
curl -fsSL https://marketer-app.com/agent/docker-compose.yml -o docker-compose.yml

# Prompt for API key
read -p "Enter your Agent API Key: " AGENT_API_KEY
echo "AGENT_API_KEY=$AGENT_API_KEY" > .env

# Start agent
docker-compose up -d

# Verify connection
echo "Verifying connection to SaaS..."
sleep 10
docker-compose logs marketer-agent | grep "Connected successfully"

if [ $? -eq 0 ]; then
    echo "✓ Agent installed and connected!"
    echo "View logs: docker-compose -f /opt/marketer-agent/docker-compose.yml logs -f"
else
    echo "✗ Connection failed. Check logs: docker-compose -f /opt/marketer-agent/docker-compose.yml logs"
fi
```

**Agent Implementation (Golang):**

```go
// agent/main.go
package main

import (
    "context"
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"

    "github.com/gorilla/websocket"
    "github.com/ollama/ollama/api"
)

type Agent struct {
    apiKey      string
    saasURL     string
    ollamaHost  string
    agentName   string
    conn        *websocket.Conn
    ollamaClient *api.Client
    ctx         context.Context
    cancel      context.CancelFunc
}

type LLMRequest struct {
    ID       string            `json:"id"`
    Model    string            `json:"model"`
    Messages []Message         `json:"messages"`
    Options  map[string]interface{} `json:"options,omitempty"`
}

type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

type LLMResponse struct {
    RequestID string  `json:"request_id"`
    Content   string  `json:"content"`
    Done      bool    `json:"done"`
    Error     string  `json:"error,omitempty"`
}

func NewAgent() *Agent {
    ctx, cancel := context.WithCancel(context.Background())

    return &Agent{
        apiKey:     os.Getenv("AGENT_API_KEY"),
        saasURL:    os.Getenv("SAAS_URL"),
        ollamaHost: os.Getenv("OLLAMA_HOST"),
        agentName:  os.Getenv("AGENT_NAME"),
        ctx:        ctx,
        cancel:     cancel,
    }
}

func (a *Agent) Connect() error {
    // Add authentication header
    header := http.Header{}
    header.Add("Authorization", "Bearer "+a.apiKey)
    header.Add("X-Agent-Name", a.agentName)

    // Connect to SaaS WebSocket
    conn, _, err := websocket.DefaultDialer.Dial(a.saasURL+"/agent/connect", header)
    if err != nil {
        return fmt.Errorf("failed to connect to SaaS: %w", err)
    }
    a.conn = conn

    // Initialize Ollama client
    ollamaURL, _ := url.Parse(a.ollamaHost)
    a.ollamaClient = api.NewClient(ollamaURL, http.DefaultClient)

    log.Println("✓ Agent connected successfully")
    return nil
}

func (a *Agent) Listen() {
    defer a.conn.Close()

    // Send heartbeat every 30 seconds
    go a.sendHeartbeat()

    for {
        var req LLMRequest
        err := a.conn.ReadJSON(&req)
        if err != nil {
            log.Printf("Read error: %v", err)

            // Attempt reconnection
            time.Sleep(5 * time.Second)
            if err := a.Connect(); err != nil {
                log.Printf("Reconnection failed: %v", err)
                continue
            }
            log.Println("✓ Reconnected successfully")
            continue
        }

        // Process request in goroutine (concurrent processing)
        go a.ProcessRequest(req)
    }
}

func (a *Agent) ProcessRequest(req LLMRequest) {
    log.Printf("Processing request %s (model: %s)", req.ID, req.Model)

    // Call local Ollama
    ctx := a.ctx

    // Convert messages to Ollama format
    ollamaMessages := make([]api.Message, len(req.Messages))
    for i, msg := range req.Messages {
        ollamaMessages[i] = api.Message{
            Role:    msg.Role,
            Content: msg.Content,
        }
    }

    chatReq := &api.ChatRequest{
        Model:    req.Model,
        Messages: ollamaMessages,
        Stream:   true,
        Options:  req.Options,
    }

    // Stream response
    respFunc := func(resp api.ChatResponse) error {
        // Send chunk back to SaaS
        llmResp := LLMResponse{
            RequestID: req.ID,
            Content:   resp.Message.Content,
            Done:      resp.Done,
        }

        if err := a.conn.WriteJSON(llmResp); err != nil {
            return fmt.Errorf("failed to send response: %w", err)
        }

        return nil
    }

    // Execute chat
    err := a.ollamaClient.Chat(ctx, chatReq, respFunc)
    if err != nil {
        log.Printf("Ollama error: %v", err)

        // Send error response
        a.conn.WriteJSON(LLMResponse{
            RequestID: req.ID,
            Error:     err.Error(),
            Done:      true,
        })
    }

    log.Printf("✓ Request %s completed", req.ID)
}

func (a *Agent) sendHeartbeat() {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            msg := map[string]string{"type": "ping"}
            if err := a.conn.WriteJSON(msg); err != nil {
                log.Printf("Heartbeat failed: %v", err)
                return
            }
        case <-a.ctx.Done():
            return
        }
    }
}

func (a *Agent) Shutdown() {
    log.Println("Shutting down agent...")
    a.cancel()
    if a.conn != nil {
        a.conn.Close()
    }
}

func main() {
    agent := NewAgent()

    // Handle graceful shutdown
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

    go func() {
        <-sigChan
        agent.Shutdown()
        os.Exit(0)
    }()

    // Connect and listen
    if err := agent.Connect(); err != nil {
        log.Fatalf("Failed to connect: %v", err)
    }

    agent.Listen()
}
```

---

## 6. SECURITY & COMPLIANCE

### 6.1 Authentication & Authorization

**Authentication (SaaS):**

```python
# backend/app/auth/clerk_integration.py
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
from fastapi import Request, HTTPException, Depends

clerk = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)

async def verify_clerk_token(request: Request) -> User:
    """Verify JWT token from Clerk."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")

    token = auth_header.split(" ")[1]

    try:
        # Verify JWT signature and claims
        session = await clerk.sessions.verify_token(
            token,
            options=AuthenticateRequestOptions()
        )

        user_id = session.user_id

        # Get or create user in local database
        user = await db.query(User).filter_by(clerk_id=user_id).first()
        if not user:
            # First time user - create account
            clerk_user = await clerk.users.get(user_id)
            user = User(
                clerk_id=user_id,
                email=clerk_user.email_addresses[0].email_address,
                role="user"
            )
            db.add(user)
            await db.commit()

        return user

    except Exception as e:
        raise HTTPException(401, f"Token verification failed: {str(e)}")

async def get_current_user(request: Request) -> User:
    """Dependency to get current authenticated user."""
    return await verify_clerk_token(request)

async def get_current_org(
    request: Request,
    user: User = Depends(get_current_user)
) -> Organization:
    """Get current organization from request context."""
    # Extract from subdomain or header
    org_slug = request.headers.get("X-Organization")
    if not org_slug:
        # Parse from subdomain: company.marketer-app.com
        host = request.headers.get("host", "")
        parts = host.split(".")
        if len(parts) >= 3:
            org_slug = parts[0]

    if not org_slug:
        raise HTTPException(400, "Organization not specified")

    org = await db.query(Organization).filter_by(slug=org_slug).first()
    if not org:
        raise HTTPException(404, "Organization not found")

    # Verify user has access to this org
    membership = await db.query(OrganizationMember).filter_by(
        user_id=user.id,
        organization_id=org.id
    ).first()

    if not membership:
        raise HTTPException(403, "Access denied to this organization")

    return org
```

**Role-Based Access Control:**

```python
# backend/app/auth/permissions.py
from enum import Enum
from typing import List

class Permission(str, Enum):
    # Projects
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"

    # Activities
    ACTIVITY_CREATE = "activity:create"
    ACTIVITY_READ = "activity:read"
    ACTIVITY_UPDATE = "activity:update"
    ACTIVITY_DELETE = "activity:delete"

    # Documents
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_READ = "document:read"
    DOCUMENT_DELETE = "document:delete"

    # Team
    TEAM_INVITE = "team:invite"
    TEAM_REMOVE = "team:remove"
    TEAM_MANAGE_ROLES = "team:manage_roles"

    # Billing
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"

    # Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_MANAGE = "settings:manage"

class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.OWNER: [p.value for p in Permission],  # All permissions

    Role.ADMIN: [
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.ACTIVITY_CREATE,
        Permission.ACTIVITY_READ,
        Permission.ACTIVITY_UPDATE,
        Permission.ACTIVITY_DELETE,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_DELETE,
        Permission.TEAM_INVITE,
        Permission.TEAM_REMOVE,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_MANAGE,
    ],

    Role.MEMBER: [
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.ACTIVITY_CREATE,
        Permission.ACTIVITY_READ,
        Permission.ACTIVITY_UPDATE,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_READ,
        Permission.SETTINGS_VIEW,
    ],

    Role.VIEWER: [
        Permission.PROJECT_READ,
        Permission.ACTIVITY_READ,
        Permission.DOCUMENT_READ,
    ]
}

def has_permission(user: User, org: Organization, permission: Permission) -> bool:
    """Check if user has specific permission in organization."""
    membership = db.query(OrganizationMember).filter_by(
        user_id=user.id,
        organization_id=org.id
    ).first()

    if not membership:
        return False

    role = Role(membership.role)
    allowed_permissions = ROLE_PERMISSIONS.get(role, [])

    return permission.value in allowed_permissions

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        async def wrapper(
            *args,
            user: User = Depends(get_current_user),
            org: Organization = Depends(get_current_org),
            **kwargs
        ):
            if not has_permission(user, org, permission):
                raise HTTPException(
                    403,
                    f"Permission denied: {permission.value} required"
                )
            return await func(*args, user=user, org=org, **kwargs)
        return wrapper
    return decorator

# Usage in routes
@app.post("/api/projects")
@require_permission(Permission.PROJECT_CREATE)
async def create_project(
    data: ProjectCreate,
    user: User,
    org: Organization
):
    # User has permission, proceed
    project = Project(
        name=data.name,
        organization_id=org.id,
        owner_id=user.id
    )
    db.add(project)
    await db.commit()
    return project
```

### 6.2 Data Encryption

**At Rest:**

```python
# backend/app/security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class EncryptionService:
    """Handles encryption of sensitive data."""

    def __init__(self):
        # Generate key from environment secret
        self.key = self._derive_key(settings.ENCRYPTION_SECRET)
        self.cipher = Fernet(self.key)

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"marketer-app-salt",  # Use unique salt in production
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string."""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string."""
        decoded = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self.cipher.decrypt(decoded)
        return decrypted.decode()

encryption_service = EncryptionService()

# Store API keys encrypted
class Organization(Base):
    __tablename__ = "organizations"

    # ... other fields ...

    _openai_api_key = Column("openai_api_key", String(500))
    _anthropic_api_key = Column("anthropic_api_key", String(500))

    @property
    def openai_api_key(self) -> str:
        if self._openai_api_key:
            return encryption_service.decrypt(self._openai_api_key)
        return None

    @openai_api_key.setter
    def openai_api_key(self, value: str):
        if value:
            self._openai_api_key = encryption_service.encrypt(value)
        else:
            self._openai_api_key = None

    @property
    def anthropic_api_key(self) -> str:
        if self._anthropic_api_key:
            return encryption_service.decrypt(self._anthropic_api_key)
        return None

    @anthropic_api_key.setter
    def anthropic_api_key(self, value: str):
        if value:
            self._anthropic_api_key = encryption_service.encrypt(value)
        else:
            self._anthropic_api_key = None
```

**In Transit:**

```nginx
# nginx.conf (TLS configuration)
server {
    listen 443 ssl http2;
    server_name api.marketer-app.com;

    # SSL certificates
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # SSL protocols and ciphers (strong security)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # HSTS (force HTTPS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Proxy to backend
    location / {
        proxy_pass http://backend-service:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 6.3 Compliance (GDPR, HIPAA, SOC2)

**Data Retention & Deletion:**

```python
# backend/app/compliance/gdpr.py
from datetime import datetime, timedelta

class GDPRCompliance:
    """GDPR compliance utilities."""

    @staticmethod
    async def export_user_data(user_id: int) -> Dict[str, Any]:
        """Export all user data (GDPR Article 20 - Right to data portability)."""
        user = await db.query(User).get(user_id)

        # Collect all user data
        data = {
            "user_profile": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "role": user.role
            },
            "organizations": [],
            "projects": [],
            "activities": [],
            "documents": []
        }

        # Organizations
        memberships = await db.query(OrganizationMember).filter_by(user_id=user_id).all()
        for membership in memberships:
            org = await db.query(Organization).get(membership.organization_id)
            data["organizations"].append({
                "name": org.name,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat()
            })

            # Projects in this org
            projects = await db.query(Project).filter_by(
                organization_id=org.id
            ).all()
            for project in projects:
                data["projects"].append({
                    "name": project.name,
                    "description": project.description,
                    "created_at": project.created_at.isoformat()
                })

                # Activities in this project
                campaigns = await db.query(Campaign).filter_by(project_id=project.id).all()
                for campaign in campaigns:
                    activities = await db.query(Activity).filter_by(
                        campaign_id=campaign.id
                    ).all()
                    for activity in activities:
                        data["activities"].append({
                            "topic": activity.topic,
                            "type": activity.type,
                            "content": activity.content,
                            "created_at": activity.created_at.isoformat()
                        })

                # Documents
                documents = await db.query(Document).filter_by(project_id=project.id).all()
                for doc in documents:
                    data["documents"].append({
                        "filename": doc.filename,
                        "upload_date": doc.created_at.isoformat(),
                        "size_bytes": doc.file_size
                    })

        return data

    @staticmethod
    async def delete_user_data(user_id: int, keep_anonymized: bool = False):
        """Delete all user data (GDPR Article 17 - Right to erasure)."""
        user = await db.query(User).get(user_id)

        if keep_anonymized:
            # Anonymize instead of delete (for compliance records)
            user.email = f"deleted_user_{user.id}@anonymized.local"
            user.clerk_id = None

            # Anonymize activities (keep for analytics)
            activities = await db.query(Activity).filter_by(owner_id=user_id).all()
            for activity in activities:
                activity.content = "[DELETED]"

        else:
            # Full deletion
            # 1. Remove from organizations
            await db.query(OrganizationMember).filter_by(user_id=user_id).delete()

            # 2. Delete activities
            await db.query(Activity).filter_by(owner_id=user_id).delete()

            # 3. Delete documents from storage
            documents = await db.query(Document).filter_by(owner_id=user_id).all()
            for doc in documents:
                # Delete from S3 or local storage
                storage_service.delete_file(doc.file_path)
                await db.delete(doc)

            # 4. Delete user record
            await db.delete(user)

        await db.commit()

    @staticmethod
    async def anonymize_old_data(days: int = 365):
        """Anonymize data older than specified days (data minimization)."""
        cutoff_date = datetime.now() - timedelta(days=days)

        # Anonymize old activities
        old_activities = await db.query(Activity).filter(
            Activity.created_at < cutoff_date,
            Activity.status == "completed"
        ).all()

        for activity in old_activities:
            # Keep metadata for analytics, remove PII
            activity.content = {"anonymized": True}

        await db.commit()

        logger.info(f"Anonymized {len(old_activities)} old activities")

# GDPR endpoints
@app.post("/api/gdpr/export-data")
async def export_my_data(user: User = Depends(get_current_user)):
    """Export all user data (GDPR compliance)."""
    data = await GDPRCompliance.export_user_data(user.id)

    # Return as downloadable JSON
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=my_data_{user.id}.json"
        }
    )

@app.post("/api/gdpr/delete-account")
async def delete_my_account(
    confirmation: str = Body(..., embed=True),
    user: User = Depends(get_current_user)
):
    """Delete user account and all data (GDPR compliance)."""
    if confirmation != "DELETE":
        raise HTTPException(400, "Confirmation required")

    await GDPRCompliance.delete_user_data(user.id, keep_anonymized=False)

    return {"message": "Account deleted successfully"}
```

**Audit Logging:**

```python
# backend/app/compliance/audit.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

class AuditLog(Base):
    """Audit trail for compliance."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)

    # Who
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    ip_address = Column(String(45))  # IPv6 support

    # What
    action = Column(String(100), index=True)  # "user.login", "document.upload", etc.
    resource_type = Column(String(50))  # "project", "activity", "document"
    resource_id = Column(Integer)

    # Details
    details = Column(JSON)  # Additional context
    status = Column(String(20))  # "success", "failure"

    # Compliance
    retention_days = Column(Integer, default=2555)  # 7 years for some regulations

async def log_audit_event(
    user: Optional[User],
    organization: Optional[Organization],
    action: str,
    resource_type: str,
    resource_id: Optional[int],
    details: Dict[str, Any],
    request: Request,
    status: str = "success"
):
    """Log an audit event."""
    log = AuditLog(
        user_id=user.id if user else None,
        organization_id=organization.id if organization else None,
        ip_address=request.client.host,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        status=status
    )
    db.add(log)
    await db.commit()

# Middleware to automatically log API requests
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # Skip health checks
    if request.url.path in ["/health", "/ready", "/metrics"]:
        return await call_next(request)

    user = None
    org = None

    try:
        # Try to get user and org
        if "Authorization" in request.headers:
            user = await get_current_user(request)
            org = await get_current_org(request, user)
    except:
        pass

    # Process request
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Log if sensitive operation
    if request.method in ["POST", "PUT", "DELETE"]:
        await log_audit_event(
            user=user,
            organization=org,
            action=f"{request.method} {request.url.path}",
            resource_type=extract_resource_type(request.url.path),
            resource_id=extract_resource_id(request.url.path),
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000)
            },
            request=request,
            status="success" if response.status_code < 400 else "failure"
        )

    return response
```

**HIPAA Compliance (Healthcare):**

```python
# backend/app/compliance/hipaa.py
class HIPAACompliance:
    """HIPAA compliance for healthcare customers."""

    # PHI (Protected Health Information) fields
    PHI_FIELDS = [
        "patient_name",
        "medical_record_number",
        "health_plan_number",
        "ssn",
        "email",  # If contains PHI
        "ip_address",
        "biometric_data"
    ]

    @staticmethod
    def redact_phi(content: str) -> str:
        """Redact PHI from content before cloud processing."""
        # Pattern matching for common PHI
        import re

        # SSN: XXX-XX-XXXX
        content = re.sub(r'\d{3}-\d{2}-\d{4}', '[SSN REDACTED]', content)

        # Medical record numbers: MRN followed by digits
        content = re.sub(r'MRN:?\s*\d+', '[MRN REDACTED]', content, flags=re.IGNORECASE)

        # Email addresses (if they contain PHI)
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]', content)

        return content

    @staticmethod
    async def ensure_local_processing(org: Organization) -> bool:
        """Ensure org is configured for local LLM processing (no PHI to cloud)."""
        if org.llm_mode != "local_agent":
            raise HTTPException(
                403,
                "HIPAA compliance requires local LLM processing. Please configure local agent."
            )

        # Verify agent is connected
        agent_status = await check_agent_status(org.id)
        if agent_status != "connected":
            raise HTTPException(
                503,
                "Local agent not connected. Cannot process PHI without local LLM."
            )

        return True

    @staticmethod
    async def log_phi_access(
        user: User,
        org: Organization,
        resource_type: str,
        resource_id: int,
        action: str
    ):
        """Log PHI access for HIPAA audit trail."""
        await log_audit_event(
            user=user,
            organization=org,
            action=f"phi.{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "phi_access": True,
                "reason": "Content generation with sensitive data"
            },
            status="success"
        )

# Middleware for HIPAA organizations
@app.middleware("http")
async def hipaa_middleware(request: Request, call_next):
    try:
        org = await get_current_org(request)

        # Check if org requires HIPAA compliance
        if org.compliance_mode == "hipaa":
            # Ensure HTTPS
            if not request.url.scheme == "https":
                raise HTTPException(403, "HTTPS required for HIPAA compliance")

            # Ensure local processing for content generation
            if request.url.path.startswith("/api/workflows"):
                await HIPAACompliance.ensure_local_processing(org)

    except Exception as e:
        # Don't block non-HIPAA orgs
        pass

    response = await call_next(request)
    return response
```

---

## 7. DATABASE SCHEMA

*(Continue with complete database schema, API specs, UI specs...)*

Due to length constraints, I'll create this as a comprehensive document. Let me continue:
