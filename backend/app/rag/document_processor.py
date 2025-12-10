"""
Document Processing for RAG
============================

Handles document upload, text extraction, chunking, and embedding storage.
"""

import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents for RAG: extract text, chunk, and store embeddings."""

    def __init__(self):
        """Initialize document processor."""
        pass

    async def process_document(
        self,
        file_path: str,
        file_type: str,
        doc_id: int,
        original_filename: str,
        project_name: str = "General"
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Process a document: extract text, chunk it, and return chunks.

        Args:
            file_path: Path to the uploaded file
            file_type: File extension (pdf, docx, txt, md)
            doc_id: Database document ID
            original_filename: Original filename
            project_name: Project name for categorization

        Returns:
            Tuple of (success: bool, chunk_count: int, error_message: Optional[str])
        """
        try:
            # Step 1: Extract text from document
            logger.info(f"Extracting text from {original_filename} (type: {file_type})")
            text = await self._extract_text(file_path, file_type)

            if not text or len(text.strip()) < 50:
                return False, 0, f"Document contains insufficient text (< 50 characters)"

            # Step 2: Chunk the text
            logger.info(f"Chunking document {doc_id}: {len(text)} characters")
            chunks = self._chunk_text(text, max_chunk_size=800, overlap=100)

            if not chunks:
                return False, 0, "Failed to create chunks from document"

            logger.info(f"Created {len(chunks)} chunks from {original_filename}")

            # Step 3: Create chunk metadata
            chunk_data = []
            for idx, chunk_text in enumerate(chunks):
                chunk_data.append({
                    "chunk_id": f"doc{doc_id}_chunk{idx}",
                    "document_id": doc_id,
                    "document_name": original_filename,
                    "project": project_name,
                    "text": chunk_text,
                    "chunk_index": idx,
                    "created_at": datetime.utcnow().isoformat()
                })

            # Step 4: Store chunks in vector store (handled externally)
            # This function returns the chunks for storage
            return True, len(chunks), None

        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {e}", exc_info=True)
            return False, 0, str(e)

    async def _extract_text(self, file_path: str, file_type: str) -> str:
        """
        Extract text from a document file.

        Args:
            file_path: Path to the file
            file_type: File extension

        Returns:
            Extracted text
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_type == "txt":
            return path.read_text(encoding="utf-8", errors="ignore")

        elif file_type == "md":
            return path.read_text(encoding="utf-8", errors="ignore")

        elif file_type == "pdf":
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text_parts = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    return "\n\n".join(text_parts)
            except ImportError:
                # Fallback: try pdfplumber
                try:
                    import pdfplumber
                    text_parts = []
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                    return "\n\n".join(text_parts)
                except ImportError:
                    raise ImportError(
                        "PDF processing requires PyPDF2 or pdfplumber. "
                        "Install with: pip install PyPDF2 or pip install pdfplumber"
                    )

        elif file_type == "docx":
            try:
                import docx
                doc = docx.Document(file_path)
                paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                return "\n\n".join(paragraphs)
            except ImportError:
                raise ImportError(
                    "DOCX processing requires python-docx. "
                    "Install with: pip install python-docx"
                )

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _chunk_text(
        self,
        text: str,
        max_chunk_size: int = 800,
        overlap: int = 100
    ) -> List[str]:
        """
        Split text into overlapping chunks respecting paragraph boundaries.

        Args:
            text: Input text
            max_chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if not paragraphs:
            # Fallback: split by newlines
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # If adding this paragraph exceeds max size, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > max_chunk_size:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    # Take last 'overlap' characters as start of new chunk
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        # Handle case where a single paragraph is too long
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chunk_size:
                final_chunks.append(chunk)
            else:
                # Split long chunk by sentences
                sentences = chunk.replace('. ', '.|').split('|')
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) + 1 > max_chunk_size:
                        if temp_chunk:
                            final_chunks.append(temp_chunk.strip())
                        temp_chunk = sent
                    else:
                        temp_chunk += " " + sent if temp_chunk else sent
                if temp_chunk:
                    final_chunks.append(temp_chunk.strip())

        return final_chunks

    def get_chunk_stats(self, chunks: List[str]) -> Dict[str, Any]:
        """
        Get statistics about chunks.

        Args:
            chunks: List of text chunks

        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {
                "count": 0,
                "avg_length": 0,
                "min_length": 0,
                "max_length": 0,
                "total_chars": 0
            }

        lengths = [len(c) for c in chunks]

        return {
            "count": len(chunks),
            "avg_length": int(sum(lengths) / len(lengths)),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_chars": sum(lengths)
        }
