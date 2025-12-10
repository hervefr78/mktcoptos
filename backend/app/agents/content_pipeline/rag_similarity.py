"""
RAG Style Similarity Analysis
Calculates how well generated content matches RAG document styles
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class RAGSimilarityAnalyzer:
    """Analyzes style similarity between generated content and RAG documents."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with a sentence transformer model."""
        self._model = None
        self._model_name = model_name

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            try:
                self._model = SentenceTransformer(self._model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model

    def calculate_document_similarity(
        self,
        generated_content: str,
        rag_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate style similarity between generated content and RAG documents.

        Args:
            generated_content: The generated text
            rag_chunks: List of RAG chunks that were used

        Returns:
            Dictionary with similarity metrics per document
        """
        if not generated_content or not rag_chunks:
            return {
                "overall_similarity": 0.0,
                "document_similarities": [],
                "method": "embedding_cosine"
            }

        try:
            model = self._load_model()

            # Encode generated content
            content_embedding = model.encode([generated_content])[0]

            # Group chunks by document
            docs = {}
            for chunk in rag_chunks:
                doc_id = chunk.get("document_id")
                if doc_id not in docs:
                    docs[doc_id] = {
                        "id": doc_id,
                        "name": chunk.get("document_name", "Unknown"),
                        "chunks": []
                    }
                docs[doc_id]["chunks"].append(chunk)

            # Calculate similarity for each document
            doc_similarities = []
            for doc_id, doc_data in docs.items():
                # Combine all chunk texts from this document
                chunk_texts = [c.get("full_text") or c.get("text", "") for c in doc_data["chunks"]]

                # Encode chunks
                chunk_embeddings = model.encode(chunk_texts)

                # Calculate cosine similarity with generated content
                similarities = [
                    self._cosine_similarity(content_embedding, chunk_emb)
                    for chunk_emb in chunk_embeddings
                ]

                avg_similarity = np.mean(similarities) if similarities else 0.0
                max_similarity = np.max(similarities) if similarities else 0.0

                doc_similarities.append({
                    "document_id": doc_id,
                    "document_name": doc_data["name"],
                    "avg_similarity": round(float(avg_similarity), 3),
                    "max_similarity": round(float(max_similarity), 3),
                    "chunks_analyzed": len(chunk_texts)
                })

            # Sort by average similarity
            doc_similarities.sort(key=lambda x: x["avg_similarity"], reverse=True)

            # Calculate overall similarity (weighted average)
            total_chunks = sum(d["chunks_analyzed"] for d in doc_similarities)
            overall = sum(
                d["avg_similarity"] * d["chunks_analyzed"]
                for d in doc_similarities
            ) / total_chunks if total_chunks > 0 else 0.0

            return {
                "overall_similarity": round(float(overall), 3),
                "document_similarities": doc_similarities,
                "method": "embedding_cosine",
                "model": self._model_name
            }

        except Exception as e:
            logger.error(f"Error calculating document similarity: {e}")
            return {
                "overall_similarity": 0.0,
                "document_similarities": [],
                "error": str(e)
            }

    def calculate_sentence_attribution(
        self,
        generated_content: str,
        rag_chunks: List[Dict[str, Any]],
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Attribute sentences in generated content to RAG chunks.

        Args:
            generated_content: The generated text
            rag_chunks: List of RAG chunks
            threshold: Similarity threshold for attribution

        Returns:
            List of sentences with their attributed chunks
        """
        if not generated_content or not rag_chunks:
            return []

        try:
            model = self._load_model()

            # Split content into sentences
            sentences = self._split_sentences(generated_content)

            if not sentences:
                return []

            # Encode all sentences
            sentence_embeddings = model.encode(sentences)

            # Encode all chunks
            chunk_texts = [c.get("full_text") or c.get("text", "") for c in rag_chunks]
            chunk_embeddings = model.encode(chunk_texts)

            # Find best matching chunk for each sentence
            attributions = []
            for idx, (sentence, sent_emb) in enumerate(zip(sentences, sentence_embeddings)):
                # Calculate similarity with all chunks
                similarities = [
                    self._cosine_similarity(sent_emb, chunk_emb)
                    for chunk_emb in chunk_embeddings
                ]

                # Find best match
                max_sim_idx = int(np.argmax(similarities))
                max_sim = float(similarities[max_sim_idx])

                attribution = {
                    "sentence_index": idx,
                    "sentence": sentence,
                    "sentence_length": len(sentence),
                }

                # Only attribute if similarity exceeds threshold
                if max_sim >= threshold:
                    best_chunk = rag_chunks[max_sim_idx]
                    attribution.update({
                        "attributed": True,
                        "chunk_id": best_chunk.get("chunk_id"),
                        "document_id": best_chunk.get("document_id"),
                        "document_name": best_chunk.get("document_name"),
                        "similarity": round(max_sim, 3),
                        "chunk_preview": (best_chunk.get("text", ""))[:100]
                    })
                else:
                    attribution["attributed"] = False
                    attribution["similarity"] = round(max_sim, 3)

                attributions.append(attribution)

            return attributions

        except Exception as e:
            logger.error(f"Error calculating sentence attribution: {e}")
            return []

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / norm_product if norm_product > 0 else 0.0

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter (can be improved with spaCy/nltk)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out very short sentences
        return [s.strip() for s in sentences if len(s.strip()) > 10]
