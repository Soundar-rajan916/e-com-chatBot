import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

# Ensure HuggingFace cache is located inside workspace if not explicitly configured
workspace_hf_cache = Path(__file__).resolve().parent.parent.parent / ".cache" / "huggingface"
if workspace_hf_cache.exists():
    os.environ.setdefault("HF_HOME", str(workspace_hf_cache))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

from app.config import get_settings  # noqa: E402

logger = logging.getLogger("app.services.embeddings")


class BaseEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class Embedder(BaseEmbedder):
    """
    Multilingual Sentence-Transformers embedder wrapper.
    Automatically prefixes queries with 'query: ' and passages with 'passage: ' (for e5 models).
    Runs CPU model encoding in a worker thread via asyncio.to_thread to avoid blocking the event loop.
    """

    _instance: Optional["Embedder"] = None
    _model = None

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.query_prefix = settings.EMBEDDING_QUERY_PREFIX
        self.passage_prefix = settings.EMBEDDING_PASSAGE_PREFIX

    @classmethod
    def get_instance(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = Embedder()
        return cls._instance

    def _load_model(self):
        if self._model is None:
            logger.info("Loading embedding model %s on CPU...", self.model_name)
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(self.model_name, device="cpu", local_files_only=True)
            except Exception:
                self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def _sync_encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"{self.passage_prefix}{t}" for t in texts]
        return await asyncio.to_thread(self._sync_encode, prefixed)

    async def embed_query(self, text: str) -> list[float]:
        prefixed = [f"{self.query_prefix}{text}"]
        results = await asyncio.to_thread(self._sync_encode, prefixed)
        return results[0]


class FakeEmbedder(BaseEmbedder):
    """
    Deterministic, hash-based fake embedder for tests.
    Does not require downloading weights or loading PyTorch models.
    Projects token bags into a 384-dimensional space so overlapping vocabularies
    score high cosine similarity while disjoint texts score low.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _vectorize(self, text: str) -> list[float]:
        words = [w for w in text.lower().split() if w]
        if not words:
            vec = np.zeros(self.dimension, dtype=np.float32)
            vec[0] = 1.0
            return vec.tolist()

        combined_vec = np.zeros(self.dimension, dtype=np.float32)
        for word in words:
            # Deterministic pseudo-random vector for each token
            seed = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            token_vec = rng.randn(self.dimension).astype(np.float32)
            token_norm = np.linalg.norm(token_vec)
            if token_norm > 0:
                combined_vec += token_vec / token_norm

        norm = np.linalg.norm(combined_vec)
        if norm > 0:
            combined_vec /= norm
        else:
            combined_vec[0] = 1.0

        return combined_vec.tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vectorize(text)


def get_embedder() -> BaseEmbedder:
    return Embedder.get_instance()
