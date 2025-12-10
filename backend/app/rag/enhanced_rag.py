"""
Enhanced RAG Services for Brand Voice
======================================

Implements advanced RAG strategies:
- Context-aware chunking
- Chunk enrichment with metadata
- Query expansion
- Cross-encoder reranking (Phase 2)
- Hierarchical RAG (Phase 2)
"""

import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder

logger = logging.getLogger(__name__)


# =============================================================================
# RERANKER SERVICE (Phase 2 - Strategy 1)
# =============================================================================

class RerankerService:
    """
    Cross-encoder reranker for improved retrieval precision.

    Uses a cross-encoder model to score query-document pairs more accurately
    than bi-encoder similarity search alone.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the reranker.

        Args:
            model_name: Cross-encoder model to use. Options:
                - "cross-encoder/ms-marco-MiniLM-L-6-v2" (fast, good quality)
                - "cross-encoder/ms-marco-MiniLM-L-12-v2" (better quality)
                - "BAAI/bge-reranker-base" (multilingual)
        """
        self._model = None
        self._model_name = model_name

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            logger.info(f"Loading reranker model: {self._model_name}")
            try:
                self._model = CrossEncoder(self._model_name)
                logger.info("Reranker model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                raise
        return self._model

    def rerank(
        self,
        query: str,
        chunks: List["EnrichedChunk"],
        top_k: int = 10
    ) -> List[Tuple["EnrichedChunk", float]]:
        """
        Rerank chunks based on relevance to query.

        Args:
            query: The search query
            chunks: List of chunks to rerank
            top_k: Number of top results to return

        Returns:
            List of (chunk, score) tuples, sorted by relevance
        """
        if not chunks:
            return []

        model = self._load_model()

        # Create query-document pairs
        pairs = [(query, chunk.text) for chunk in chunks]

        # Get scores from cross-encoder
        scores = model.predict(pairs)

        # Combine chunks with scores and sort
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        return scored_chunks[:top_k]

    def rerank_with_context(
        self,
        query: str,
        chunks: List["EnrichedChunk"],
        top_k: int = 10,
        include_summary: bool = True
    ) -> List[Tuple["EnrichedChunk", float]]:
        """
        Rerank using both text and context summary for better matching.

        Args:
            query: The search query
            chunks: List of chunks to rerank
            top_k: Number of top results to return
            include_summary: Whether to include context_summary in scoring

        Returns:
            List of (chunk, score) tuples
        """
        if not chunks:
            return []

        model = self._load_model()

        # Create enriched text for each chunk
        texts = []
        for chunk in chunks:
            if include_summary and chunk.context_summary:
                enriched_text = f"{chunk.context_summary}\n\n{chunk.text}"
            else:
                enriched_text = chunk.text
            texts.append(enriched_text)

        # Create query-document pairs
        pairs = [(query, text) for text in texts]

        # Get scores
        scores = model.predict(pairs)

        # Combine and sort
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        return scored_chunks[:top_k]


# =============================================================================
# HIERARCHICAL RAG SERVICE (Phase 2 - Strategy 9)
# =============================================================================

class HierarchicalRAGService:
    """
    Two-stage retrieval: first find best documents, then best chunks within them.

    This improves coherence by ensuring chunks come from the most relevant documents.
    """

    def __init__(self, embedding_model: SentenceTransformer = None):
        self.embedding_model = embedding_model or SentenceTransformer("all-MiniLM-L6-v2")
        self._doc_embeddings: Dict[str, np.ndarray] = {}
        self._doc_summaries: Dict[str, str] = {}

    def build_document_index(self, chunks: List["EnrichedChunk"]):
        """
        Build document-level embeddings by aggregating chunk information.

        Args:
            chunks: All chunks to index
        """
        # Group chunks by document
        doc_chunks: Dict[str, List["EnrichedChunk"]] = defaultdict(list)
        for chunk in chunks:
            doc_chunks[chunk.doc_id].append(chunk)

        # Create document summaries and embeddings
        for doc_id, doc_chunk_list in doc_chunks.items():
            # Combine chunk summaries for document representation
            summaries = [c.context_summary for c in doc_chunk_list if c.context_summary]
            if summaries:
                doc_summary = " ".join(summaries[:5])  # Use first 5 summaries
            else:
                # Use first part of first chunk
                doc_summary = doc_chunk_list[0].text[:500]

            self._doc_summaries[doc_id] = doc_summary

            # Create embedding for document
            embedding = self.embedding_model.encode([doc_summary])[0]
            self._doc_embeddings[doc_id] = embedding

        logger.info(f"Built hierarchical index for {len(self._doc_embeddings)} documents")

    def retrieve_hierarchical(
        self,
        query: str,
        chunks: List["EnrichedChunk"],
        top_docs: int = 3,
        chunks_per_doc: int = 5
    ) -> List["EnrichedChunk"]:
        """
        Two-stage retrieval: documents first, then chunks.

        Args:
            query: Search query
            chunks: All available chunks
            top_docs: Number of top documents to consider
            chunks_per_doc: Number of chunks to retrieve per document

        Returns:
            List of relevant chunks from top documents
        """
        if not self._doc_embeddings:
            # Build index if not done
            self.build_document_index(chunks)

        # Stage 1: Find top documents
        query_embedding = self.embedding_model.encode([query])[0]

        doc_scores = []
        for doc_id, doc_embedding in self._doc_embeddings.items():
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            doc_scores.append((doc_id, similarity))

        # Sort by similarity
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        top_doc_ids = [doc_id for doc_id, _ in doc_scores[:top_docs]]

        logger.info(f"Hierarchical RAG: selected top {len(top_doc_ids)} documents")

        # Stage 2: Get chunks from top documents
        # Group chunks by document
        doc_chunks: Dict[str, List["EnrichedChunk"]] = defaultdict(list)
        for chunk in chunks:
            if chunk.doc_id in top_doc_ids:
                doc_chunks[chunk.doc_id].append(chunk)

        # Get embeddings for chunks in top docs
        results = []
        for doc_id in top_doc_ids:
            if doc_id not in doc_chunks:
                continue

            doc_chunk_list = doc_chunks[doc_id]

            # Score chunks within document
            chunk_texts = [c.text for c in doc_chunk_list]
            chunk_embeddings = self.embedding_model.encode(chunk_texts)

            chunk_scores = []
            for i, chunk in enumerate(doc_chunk_list):
                similarity = np.dot(query_embedding, chunk_embeddings[i]) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embeddings[i])
                )
                chunk_scores.append((chunk, similarity))

            # Sort and take top chunks from this doc
            chunk_scores.sort(key=lambda x: x[1], reverse=True)
            for chunk, _ in chunk_scores[:chunks_per_doc]:
                results.append(chunk)

        return results


# =============================================================================
# ENRICHED CHUNK MODEL
# =============================================================================

class EnrichedChunk:
    """Represents a chunk with metadata for enhanced RAG."""

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        text: str,
        context_summary: str = "",
        source_type: str = "other",
        style_tags: List[str] = None,
        content_tags: List[str] = None,
        audience_tags: List[str] = None,
        created_at: str = None
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.text = text
        self.context_summary = context_summary
        self.source_type = source_type
        self.style_tags = style_tags or []
        self.content_tags = content_tags or []
        self.audience_tags = audience_tags or []
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "context_summary": self.context_summary,
            "source_type": self.source_type,
            "style_tags": self.style_tags,
            "content_tags": self.content_tags,
            "audience_tags": self.audience_tags,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnrichedChunk":
        return cls(**data)


# =============================================================================
# CHUNK ENRICHMENT SERVICE
# =============================================================================

class ChunkEnrichmentService:
    """
    Enriches text chunks with metadata using LLM.

    Adds:
    - context_summary: 1-sentence summary
    - style_tags: style characteristics
    - content_tags: content type tags
    - audience_tags: target audience tags
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service

    async def enrich_chunk(
        self,
        text: str,
        doc_id: str,
        source_type: str = "other"
    ) -> EnrichedChunk:
        """
        Enrich a single chunk with metadata.

        Args:
            text: The chunk text
            doc_id: Document identifier
            source_type: Type of source (blog_post, linkedin_post, etc.)

        Returns:
            EnrichedChunk with metadata
        """
        chunk_id = f"chunk_{uuid.uuid4().hex[:12]}"

        if not self.llm_service:
            # Return basic chunk without enrichment
            return EnrichedChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=text,
                source_type=source_type
            )

        # Use LLM to extract metadata
        prompt = f"""Analyze this text chunk and extract metadata for a brand voice RAG system.

Text:
{text}

Source type: {source_type}

Respond with JSON only:
{{
  "context_summary": "One sentence summary of what this chunk is about",
  "style_tags": ["2-4 style descriptors like: provocative, concise, technical, friendly, formal, casual, no_fluff, data_driven"],
  "content_tags": ["1-3 content type tags like: product_launch, thought_leadership, how_to, case_study, announcement"],
  "audience_tags": ["1-3 audience tags like: CMO, developers, SaaS_founders, marketers, executives"]
}}"""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are a metadata extraction assistant. Respond only with valid JSON.",
                temperature=0.2,
                max_tokens=500
            )

            # Parse response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            metadata = json.loads(cleaned.strip())

            return EnrichedChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=text,
                context_summary=metadata.get("context_summary", ""),
                source_type=source_type,
                style_tags=metadata.get("style_tags", []),
                content_tags=metadata.get("content_tags", []),
                audience_tags=metadata.get("audience_tags", [])
            )

        except Exception as e:
            logger.error(f"Chunk enrichment failed: {e}")
            return EnrichedChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=text,
                source_type=source_type
            )

    async def enrich_chunks(
        self,
        texts: List[str],
        doc_id: str,
        source_type: str = "other"
    ) -> List[EnrichedChunk]:
        """Enrich multiple chunks."""
        enriched = []
        for text in texts:
            chunk = await self.enrich_chunk(text, doc_id, source_type)
            enriched.append(chunk)
        return enriched


# =============================================================================
# QUERY EXPANSION SERVICE
# =============================================================================

class QueryExpansionService:
    """
    Expands a single query into multiple variants for better retrieval.
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service

    async def expand_query(
        self,
        topic: str,
        content_type: str,
        audience: str,
        brand_voice: str,
        goal: str
    ) -> List[str]:
        """
        Generate multiple query variants for style retrieval.

        Args:
            topic: Content topic
            content_type: Type of content
            audience: Target audience
            brand_voice: Brand voice description
            goal: Content goal

        Returns:
            List of 3-5 query variants
        """
        # Base query
        base_query = f"Examples of {content_type} written for {audience} with a {brand_voice} tone, focusing on {goal}."

        if not self.llm_service:
            # Return basic variants without LLM
            return [
                base_query,
                f"{brand_voice} style {content_type} for {audience}",
                f"{content_type} examples with {brand_voice} voice"
            ]

        prompt = f"""Generate 4 search query variants for finding brand voice examples.

Context:
- Topic: {topic}
- Content type: {content_type}
- Audience: {audience}
- Brand voice: {brand_voice}
- Goal: {goal}

Generate diverse queries that will help find relevant style examples.
Include synonyms and variations.

Respond with JSON only:
{{
  "queries": [
    "query 1",
    "query 2",
    "query 3",
    "query 4"
  ]
}}"""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are a search query optimization assistant. Respond only with valid JSON.",
                temperature=0.5,
                max_tokens=300
            )

            # Parse response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            data = json.loads(cleaned.strip())
            queries = [base_query] + data.get("queries", [])

            return queries[:5]  # Return max 5 queries

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [base_query]


# =============================================================================
# ENHANCED VECTOR STORE
# =============================================================================

class EnhancedVectorStore:
    """
    Vector store with support for enriched chunks and metadata filtering.

    Phase 2 features:
    - Cross-encoder reranking for improved precision
    - Hierarchical RAG (document-level then chunk-level)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.data_dir = Path(__file__).resolve().parents[2] / "data" / "brand_voice"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.data_dir / "brand_voice.index"
        self.chunks_path = self.data_dir / "chunks.json"

        self.chunks: List[EnrichedChunk] = []
        self.embeddings: np.ndarray = None

        # Phase 2 services (lazy initialization)
        self._reranker: Optional[RerankerService] = None
        self._hierarchical_service: Optional[HierarchicalRAGService] = None

        self._load()

    @property
    def reranker(self) -> RerankerService:
        """Lazy load reranker service."""
        if self._reranker is None:
            self._reranker = RerankerService()
        return self._reranker

    @property
    def hierarchical_service(self) -> HierarchicalRAGService:
        """Lazy load hierarchical RAG service."""
        if self._hierarchical_service is None:
            self._hierarchical_service = HierarchicalRAGService(self.model)
        return self._hierarchical_service

    def _load(self):
        """Load existing chunks and embeddings."""
        if self.chunks_path.exists():
            data = json.loads(self.chunks_path.read_text())
            self.chunks = [EnrichedChunk.from_dict(c) for c in data.get("chunks", [])]

            if self.index_path.exists() and len(self.chunks) > 0:
                import faiss
                index = faiss.read_index(str(self.index_path))
                self.embeddings = faiss.vector_to_array(index.reconstruct_n(0, index.ntotal))
                self.embeddings = self.embeddings.reshape(index.ntotal, -1)
            else:
                self.embeddings = None

    def _save(self):
        """Save chunks and embeddings."""
        # Save chunks
        data = {"chunks": [c.to_dict() for c in self.chunks]}
        self.chunks_path.write_text(json.dumps(data, indent=2))

        # Save embeddings
        if self.embeddings is not None and len(self.embeddings) > 0:
            import faiss
            dim = self.embeddings.shape[1]
            index = faiss.IndexFlatL2(dim)
            index.add(self.embeddings.astype("float32"))
            faiss.write_index(index, str(self.index_path))

    def add_chunks(self, chunks: List[EnrichedChunk]):
        """Add enriched chunks to the store."""
        if not chunks:
            return

        # Generate embeddings for chunk texts
        texts = [c.text for c in chunks]
        new_embeddings = self.model.encode(texts)

        # Append to existing
        self.chunks.extend(chunks)

        if self.embeddings is None:
            self.embeddings = np.array(new_embeddings).astype("float32")
        else:
            self.embeddings = np.vstack([
                self.embeddings,
                np.array(new_embeddings).astype("float32")
            ])

        self._save()
        logger.info(f"Added {len(chunks)} chunks. Total: {len(self.chunks)}")

    def similarity_search(
        self,
        query: str,
        k: int = 10,
        source_type_filter: Optional[str] = None,
        style_tags_filter: Optional[List[str]] = None,
        audience_tags_filter: Optional[List[str]] = None
    ) -> List[EnrichedChunk]:
        """
        Search for similar chunks with optional metadata filtering.

        Args:
            query: Search query
            k: Number of results
            source_type_filter: Filter by source type
            style_tags_filter: Filter by style tags (any match)
            audience_tags_filter: Filter by audience tags (any match)

        Returns:
            List of matching EnrichedChunks
        """
        if not self.chunks or self.embeddings is None:
            return []

        # Get query embedding
        query_embedding = self.model.encode([query])[0]

        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top candidates (fetch more for filtering)
        top_k = min(k * 3, len(self.chunks))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Filter and collect results
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]

            # Apply filters
            if source_type_filter and chunk.source_type != source_type_filter:
                continue

            if style_tags_filter:
                if not any(tag in chunk.style_tags for tag in style_tags_filter):
                    continue

            if audience_tags_filter:
                if not any(tag in chunk.audience_tags for tag in audience_tags_filter):
                    continue

            results.append(chunk)

            if len(results) >= k:
                break

        return results

    def search_with_expansion(
        self,
        queries: List[str],
        k: int = 10,
        use_reranking: bool = False,
        **filters
    ) -> List[EnrichedChunk]:
        """
        Search with multiple query variants and deduplicate results.

        Args:
            queries: List of query variants
            k: Number of final results
            use_reranking: Whether to apply cross-encoder reranking (Phase 2)
            **filters: Metadata filters

        Returns:
            Deduplicated list of EnrichedChunks
        """
        seen_ids = set()
        all_results = []

        for query in queries:
            results = self.similarity_search(query, k=k, **filters)
            for chunk in results:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    all_results.append(chunk)

        # Apply reranking if enabled (Phase 2)
        if use_reranking and all_results and queries:
            # Use primary query for reranking
            primary_query = queries[0]
            reranked = self.reranker.rerank_with_context(
                primary_query, all_results, top_k=k
            )
            return [chunk for chunk, _ in reranked]

        # Return top k by order of appearance (first query has priority)
        return all_results[:k]

    def similarity_search_with_reranking(
        self,
        query: str,
        k: int = 10,
        initial_k: int = 50,
        include_context: bool = True,
        **filters
    ) -> List[Tuple[EnrichedChunk, float]]:
        """
        Search with cross-encoder reranking for improved precision.

        Phase 2 feature: Two-stage retrieval:
        1. Fast bi-encoder retrieval (initial_k candidates)
        2. Cross-encoder reranking for precision

        Args:
            query: Search query
            k: Number of final results
            initial_k: Number of candidates for reranking
            include_context: Include context_summary in reranking
            **filters: Metadata filters

        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        if not self.chunks or self.embeddings is None:
            return []

        # Stage 1: Fast bi-encoder retrieval
        candidates = self.similarity_search(query, k=initial_k, **filters)

        if not candidates:
            return []

        # Stage 2: Cross-encoder reranking
        if include_context:
            reranked = self.reranker.rerank_with_context(query, candidates, top_k=k)
        else:
            reranked = self.reranker.rerank(query, candidates, top_k=k)

        logger.info(f"Reranked {len(candidates)} candidates to {len(reranked)} results")
        return reranked

    def search_hierarchical(
        self,
        query: str,
        k: int = 10,
        top_docs: int = 3,
        chunks_per_doc: int = 5,
        use_reranking: bool = True,
        **filters
    ) -> List[EnrichedChunk]:
        """
        Two-stage hierarchical retrieval for coherent results.

        Phase 2 feature: Find best documents first, then best chunks.

        Args:
            query: Search query
            k: Final number of results
            top_docs: Number of top documents to consider
            chunks_per_doc: Chunks to retrieve per document
            use_reranking: Apply cross-encoder reranking to final results
            **filters: Metadata filters (applied to chunks)

        Returns:
            List of EnrichedChunks from top documents
        """
        if not self.chunks:
            return []

        # Apply filters first
        filtered_chunks = self.chunks
        if filters:
            filtered_chunks = []
            for chunk in self.chunks:
                if filters.get("source_type_filter"):
                    if chunk.source_type != filters["source_type_filter"]:
                        continue
                if filters.get("style_tags_filter"):
                    if not any(tag in chunk.style_tags for tag in filters["style_tags_filter"]):
                        continue
                if filters.get("audience_tags_filter"):
                    if not any(tag in chunk.audience_tags for tag in filters["audience_tags_filter"]):
                        continue
                filtered_chunks.append(chunk)

        if not filtered_chunks:
            return []

        # Hierarchical retrieval
        results = self.hierarchical_service.retrieve_hierarchical(
            query, filtered_chunks, top_docs=top_docs, chunks_per_doc=chunks_per_doc
        )

        # Optionally apply reranking for final precision
        if use_reranking and results:
            reranked = self.reranker.rerank_with_context(query, results, top_k=k)
            return [chunk for chunk, _ in reranked]

        return results[:k]

    def advanced_search(
        self,
        query: str,
        k: int = 10,
        mode: str = "standard",
        query_variants: Optional[List[str]] = None,
        **kwargs
    ) -> List[EnrichedChunk]:
        """
        Unified search interface with multiple modes.

        Args:
            query: Primary search query
            k: Number of results
            mode: Search mode - "standard", "reranked", "hierarchical", "expanded"
            query_variants: Additional query variants for expansion mode
            **kwargs: Additional parameters passed to specific search methods

        Returns:
            List of EnrichedChunks
        """
        if mode == "standard":
            return self.similarity_search(query, k=k, **kwargs)

        elif mode == "reranked":
            results = self.similarity_search_with_reranking(query, k=k, **kwargs)
            return [chunk for chunk, _ in results]

        elif mode == "hierarchical":
            return self.search_hierarchical(query, k=k, **kwargs)

        elif mode == "expanded":
            queries = [query] + (query_variants or [])
            use_reranking = kwargs.pop("use_reranking", True)
            return self.search_with_expansion(
                queries, k=k, use_reranking=use_reranking, **kwargs
            )

        else:
            logger.warning(f"Unknown search mode: {mode}, using standard")
            return self.similarity_search(query, k=k, **kwargs)

    def get_all_chunks(self) -> List[EnrichedChunk]:
        """Get all stored chunks."""
        return self.chunks

    def clear(self):
        """Clear all stored data."""
        self.chunks = []
        self.embeddings = None
        if self.index_path.exists():
            self.index_path.unlink()
        if self.chunks_path.exists():
            self.chunks_path.unlink()


# =============================================================================
# CONTEXT-AWARE CHUNKING
# =============================================================================

def context_aware_chunk(
    text: str,
    max_chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """
    Split text into chunks respecting paragraph boundaries.

    Args:
        text: Input text
        max_chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If paragraph itself is too long, split by sentences
        if len(para) > max_chunk_size:
            sentences = para.replace('. ', '.|').split('|')
            for sent in sentences:
                if len(current_chunk) + len(sent) > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sent
                else:
                    current_chunk += " " + sent if current_chunk else sent
        else:
            if len(current_chunk) + len(para) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
