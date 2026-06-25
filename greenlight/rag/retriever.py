"""
Greenlight Cinema — RAG Retriever v3
======================================
Retrieves relevant screenplay chunks from ChromaDB for synopsis generation.

Now uses real screenplay chunks (scene-based) with metadata:
  source, title, genre, year, act, chunk_index, total_chunks, word_count
"""

import logging
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings

from greenlight.config import CHROMA_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL

log = logging.getLogger("greenlight.rag.retriever")


@dataclass
class RetrievedScene:
    """A single retrieved RAG result from a real screenplay."""
    document: str
    title: str
    genre: str
    source: str
    act: str
    distance: float
    year: int = 0
    chunk_index: int = 0
    total_chunks: int = 0
    word_count: int = 0


class RAGRetriever:
    """ChromaDB-backed retriever for real movie screenplays."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._initialized = False

    def _init(self):
        """Lazy initialization."""
        if self._initialized:
            return
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

            self._client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_collection(
                name=CHROMA_COLLECTION,
                embedding_function=embedding_fn,
            )
            self._initialized = True
            log.info(f"RAG retriever initialized: {self._collection.count()} documents")
        except Exception as e:
            log.warning(f"RAG retriever init failed: {e}")
            self._initialized = False

    def is_healthy(self) -> bool:
        """Check if ChromaDB is available."""
        try:
            self._init()
            return self._initialized and self._collection is not None
        except Exception:
            return False

    def get_collection_count(self) -> int:
        """Get total document count."""
        self._init()
        if not self._initialized:
            return 0
        return self._collection.count()

    def retrieve(self, genre: str, query: str, n: int = 5,
                 act: str = None) -> list[RetrievedScene]:
        """
        Retrieve relevant screenplay chunks.

        Args:
            genre: Target genre for filtering
            query: Semantic search query
            n: Number of results
            act: Optional filter: 'act_1', 'act_2', 'act_3'

        Returns:
            List of RetrievedScene objects
        """
        self._init()
        if not self._initialized:
            return []

        # Build where filter
        where_filter = None
        if act:
            where_filter = {"act": act}

        try:
            results = self._collection.query(
                query_texts=[f"{genre} {query}"],
                n_results=min(n, self._collection.count()),
                where=where_filter if where_filter else None,
            )
        except Exception as e:
            log.warning(f"ChromaDB query failed: {e}")
            # Retry without filter
            try:
                results = self._collection.query(
                    query_texts=[f"{genre} {query}"],
                    n_results=min(n, self._collection.count()),
                )
            except Exception as e2:
                log.error(f"ChromaDB query failed completely: {e2}")
                return []

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        scenes = []
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, dists):
            scenes.append(RetrievedScene(
                document=doc,
                title=meta.get("title", "Unknown"),
                genre=meta.get("genre", ""),
                source=meta.get("source", ""),
                act=meta.get("act", ""),
                distance=dist,
                year=meta.get("year", 0),
                chunk_index=meta.get("chunk_index", 0),
                total_chunks=meta.get("total_chunks", 0),
                word_count=meta.get("word_count", 0),
            ))

        return scenes

    def retrieve_by_act(self, genre: str, query: str, act: str, n: int = 3) -> list[RetrievedScene]:
        """Retrieve screenplay chunks from a specific act."""
        return self.retrieve(genre, query, n=n, act=act)

    def retrieve_mixed(self, genre: str, query: str, n: int = 5) -> list[RetrievedScene]:
        """Retrieve a mix of screenplay chunks from all acts."""
        return self.retrieve(genre, query, n=n)
