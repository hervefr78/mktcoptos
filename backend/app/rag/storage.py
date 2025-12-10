"""
RAG Storage Service
===================

Stores and retrieves RAG chunks from vector stores.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RAGStorage:
    """Storage service for RAG chunks with vector embeddings."""

    def __init__(self):
        """Initialize RAG storage with separate stores for brand voice and knowledge base."""
        self.data_dir = Path(__file__).resolve().parents[3] / "data" / "rag_storage"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Separate storage for brand_voice and knowledge_base
        self.brand_voice_path = self.data_dir / "brand_voice_chunks.json"
        self.knowledge_base_path = self.data_dir / "knowledge_base_chunks.json"
        self.embeddings_dir = self.data_dir / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)

        self._model = None  # Lazy load

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model for RAG storage...")
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model

    def store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        collection: str = "knowledge_base"
    ) -> bool:
        """
        Store chunks with their embeddings.

        Args:
            chunks: List of chunk dictionaries with text and metadata
            collection: Collection name ("brand_voice" or "knowledge_base")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate collection
            if collection not in ["brand_voice", "knowledge_base"]:
                raise ValueError(f"Invalid collection: {collection}. Must be 'brand_voice' or 'knowledge_base'")

            # Load existing chunks
            storage_path = self.brand_voice_path if collection == "brand_voice" else self.knowledge_base_path
            existing_chunks = self._load_chunks(storage_path)

            # Generate embeddings for new chunks
            model = self._load_model()
            texts = [chunk["text"] for chunk in chunks]
            embeddings = model.encode(texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding.tolist()  # Convert to list for JSON serialization

            # Append new chunks
            existing_chunks.extend(chunks)

            # Save updated chunks
            self._save_chunks(storage_path, existing_chunks)

            logger.info(f"Stored {len(chunks)} chunks in {collection} collection. Total: {len(existing_chunks)}")
            return True

        except Exception as e:
            logger.error(f"Error storing chunks in {collection}: {e}", exc_info=True)
            return False

    def retrieve_chunks(
        self,
        query: str,
        collection: str = "knowledge_base",
        k: int = 10,
        document_ids: Optional[List[int]] = None,
        project_name: Optional[str] = None,
        campaign_id: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using semantic search.

        Args:
            query: Search query
            collection: Collection to search ("brand_voice" or "knowledge_base")
            k: Number of results to return
            document_ids: Optional list of document IDs to filter by
            project_name: Optional project name to filter chunks by
            campaign_id: Optional campaign ID to filter chunks by

        Returns:
            List of relevant chunks with metadata
        """
        try:
            # Load chunks
            storage_path = self.brand_voice_path if collection == "brand_voice" else self.knowledge_base_path
            chunks = self._load_chunks(storage_path)

            if not chunks:
                logger.warning(f"No chunks found in {collection} collection")
                return []

            # Filter by campaign ID if provided
            if campaign_id is not None:
                chunks = [c for c in chunks if c.get("campaign_id") == campaign_id]
                logger.info(f"Filtered to {len(chunks)} chunks from campaign {campaign_id}")

            # Filter by project name if provided
            if project_name:
                # Check if project is in the chunk's projects array OR matches the legacy project field
                chunks = [
                    c for c in chunks
                    if project_name in c.get("projects", [c.get("project", "General")])
                ]
                logger.info(f"Filtered to {len(chunks)} chunks from project '{project_name}'")

            # Filter by document IDs if provided
            if document_ids:
                chunks = [c for c in chunks if c.get("document_id") in document_ids]
                logger.info(f"Filtered to {len(chunks)} chunks from {len(document_ids)} documents")

            if not chunks:
                return []

            # Get query embedding
            model = self._load_model()
            query_embedding = model.encode([query])[0]

            # Calculate similarities
            similarities = []
            for idx, chunk in enumerate(chunks):
                chunk_embedding = np.array(chunk.get("embedding", []))
                if len(chunk_embedding) == 0:
                    continue

                # Cosine similarity
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )
                similarities.append((idx, float(similarity)))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Get top k results
            results = []
            for idx, score in similarities[:k]:
                chunk = chunks[idx].copy()
                chunk["score"] = score  # Use "score" field for consistency with orchestrator
                chunk["similarity_score"] = score  # Keep for backward compatibility
                # Remove embedding from result (too large)
                chunk.pop("embedding", None)
                results.append(chunk)

            logger.info(f"Retrieved {len(results)} chunks from {collection} for query: '{query[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Error retrieving chunks from {collection}: {e}", exc_info=True)
            return []

    def get_document_chunks(
        self,
        document_id: int,
        collection: str = "knowledge_base"
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific document.

        Args:
            document_id: Document ID
            collection: Collection name

        Returns:
            List of chunks for the document
        """
        try:
            storage_path = self.brand_voice_path if collection == "brand_voice" else self.knowledge_base_path
            chunks = self._load_chunks(storage_path)

            doc_chunks = [c for c in chunks if c.get("document_id") == document_id]
            logger.info(f"Found {len(doc_chunks)} chunks for document {document_id}")
            return doc_chunks

        except Exception as e:
            logger.error(f"Error getting chunks for document {document_id}: {e}")
            return []

    def delete_document_chunks(
        self,
        document_id: int,
        collection: str = "knowledge_base"
    ) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document ID
            collection: Collection name

        Returns:
            Number of chunks deleted
        """
        try:
            storage_path = self.brand_voice_path if collection == "brand_voice" else self.knowledge_base_path
            chunks = self._load_chunks(storage_path)

            # Filter out chunks from this document
            remaining_chunks = [c for c in chunks if c.get("document_id") != document_id]
            deleted_count = len(chunks) - len(remaining_chunks)

            # Save filtered chunks
            self._save_chunks(storage_path, remaining_chunks)

            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}")
            return 0

    def get_stats(self, collection: str = "knowledge_base") -> Dict[str, Any]:
        """
        Get statistics about stored chunks.

        Args:
            collection: Collection name

        Returns:
            Dictionary with statistics
        """
        try:
            storage_path = self.brand_voice_path if collection == "brand_voice" else self.knowledge_base_path
            chunks = self._load_chunks(storage_path)

            if not chunks:
                return {
                    "total_chunks": 0,
                    "total_documents": 0,
                    "avg_chunks_per_doc": 0
                }

            # Count unique documents
            doc_ids = set(c.get("document_id") for c in chunks if c.get("document_id"))

            return {
                "total_chunks": len(chunks),
                "total_documents": len(doc_ids),
                "avg_chunks_per_doc": round(len(chunks) / len(doc_ids), 1) if doc_ids else 0
            }

        except Exception as e:
            logger.error(f"Error getting stats for {collection}: {e}")
            return {"error": str(e)}

    def _load_chunks(self, path: Path) -> List[Dict[str, Any]]:
        """Load chunks from JSON file."""
        if not path.exists():
            return []

        try:
            with path.open("r") as f:
                data = json.load(f)
                return data.get("chunks", [])
        except Exception as e:
            logger.error(f"Error loading chunks from {path}: {e}")
            return []

    def _save_chunks(self, path: Path, chunks: List[Dict[str, Any]]) -> None:
        """Save chunks to JSON file."""
        try:
            with path.open("w") as f:
                json.dump({"chunks": chunks, "version": "1.0"}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving chunks to {path}: {e}")
            raise
