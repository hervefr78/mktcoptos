from __future__ import annotations

from pathlib import Path
from typing import List

import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class VectorStore:
    """FAISS-backed vector store that persists to disk."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)
        self.data_dir = Path(__file__).resolve().parents[3] / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.data_dir / "faiss.index"
        self.text_path = self.data_dir / "texts.json"

        self.index = self._load_index()
        self.texts = self._load_texts()

    def _load_index(self) -> faiss.Index:
        if self.index_path.exists():
            return faiss.read_index(str(self.index_path))
        dim = self.model.get_sentence_embedding_dimension()
        return faiss.IndexFlatL2(dim)

    def _load_texts(self) -> List[str]:
        if self.text_path.exists():
            return json.loads(self.text_path.read_text())
        return []

    def add_texts(self, texts: List[str]) -> None:
        embeddings = self.model.encode(texts)
        self.index.add(np.array(embeddings).astype("float32"))
        self.texts.extend(texts)
        self._persist()

    def similarity_search(self, query: str, k: int = 5) -> List[str]:
        embedding = self.model.encode([query])
        distances, indices = self.index.search(np.array(embedding).astype("float32"), k)
        results = []
        for idx in indices[0]:
            if idx < len(self.texts):
                results.append(self.texts[idx])
        return results

    def _persist(self) -> None:
        faiss.write_index(self.index, str(self.index_path))
        self.text_path.write_text(json.dumps(self.texts))
