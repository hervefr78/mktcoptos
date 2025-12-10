# Agent Reference

This repository implements a multi-agent content-generation pipeline coordinated by a LangGraph-style orchestrator. Use this document as the canonical reference for the available agents, their responsibilities, and integration notes.

## Base abstractions
- `BaseAgent` defines the required interface for every agent (`run`, `name`, `description`) and accepts an optional `llm_client` injected at construction time.【F:backend/app/agents/base.py†L5-L25】
- `ContentPipelineAgent` adds shared prompt formatting, JSON parsing, and last-call logging for LLM-backed agents in the content pipeline.【F:backend/app/agents/content_pipeline/content_agents.py†L34-L99】
- `RAGAgent` performs retrieval-augmented generation by pulling context from the vector store before delegating to the injected LLM client.【F:backend/app/agents/rag_agent.py†L7-L44】

## Content pipeline agents
Seven specialized agents collaborate to produce, refine, and QA long-form content. Use `get_content_agent`/`get_all_content_agents` to instantiate them by ID with a shared LLM client.【F:backend/app/agents/content_pipeline/content_agents.py†L102-L778】 Key responsibilities and outputs:

1. **Trends & Keywords Agent (`trends_keywords`)** – researches the topic to surface trend summaries, primary/secondary keywords, search intent insights, and angle ideas.【F:backend/app/agents/content_pipeline/content_agents.py†L102-L173】
2. **Tone-of-Voice RAG Agent (`tone_of_voice`)** – builds a style profile from brand guidelines and retrieved style examples (formality, rhythm, rhetorical devices, do/don't rules, examples).【F:backend/app/agents/content_pipeline/content_agents.py†L176-L252】
3. **Structure & Outline Agent (`structure_outline`)** – creates a conversion-oriented outline (content promise, hook ideas, sections with objectives and key points) using research and style context.【F:backend/app/agents/content_pipeline/content_agents.py†L254-L349】
4. **Writer Agent (`writer`)** – produces the full draft in Markdown following the outline, keyword guidance, and style profile.【F:backend/app/agents/content_pipeline/content_agents.py†L351-L458】
5. **SEO Optimizer Agent (`seo_optimizer`)** – rewrites the draft for SEO and readability, returning optimized text and on-page SEO elements (focus keyword, title tag, meta description, H1, slug, links).【F:backend/app/agents/content_pipeline/content_agents.py†L462-L549】
6. **Originality & Plagiarism Agent (`originality_plagiarism`)** – scans the optimized copy for generic or plagiarized passages, assigning an originality score and suggested rewrites for flagged excerpts.【F:backend/app/agents/content_pipeline/content_agents.py†L551-L620】
7. **Final Reviewer Agent (`final_reviewer`)** – performs editorial polish, applies originality fixes, and returns final text, change log, editor notes, and suggested content variants.【F:backend/app/agents/content_pipeline/content_agents.py†L623-L721】

## Orchestration
- `ContentPipelineOrchestrator` wires the seven agents together and tracks stage state (user input, intermediate artifacts, completed stages, errors).【F:backend/app/agents/content_pipeline/orchestrator.py†L1-L173】 It runs stages sequentially: trends/keywords → tone-of-voice → outline → writer → SEO optimizer → originality check → final review.【F:backend/app/agents/content_pipeline/orchestrator.py†L94-L199】 Inject a shared `llm_client` and optional callbacks (`on_stage_start`, `on_stage_complete`) for streaming updates and logging.【F:backend/app/agents/content_pipeline/orchestrator.py†L108-L140】

## Implementation notes
- All LLM-backed agents require an `llm_client.generate` implementation; construction without one will raise an error on use.【F:backend/app/agents/content_pipeline/content_agents.py†L80-L99】
- The `ContentPipelineAgent` helper retains the last system/user prompts, raw responses, and input context to aid debugging and observability.【F:backend/app/agents/content_pipeline/content_agents.py†L34-L55】
- RAG-enabled workflows can compose `RAGAgent` for knowledge retrieval alongside the content pipeline when additional context is needed.【F:backend/app/agents/rag_agent.py†L7-L44】
