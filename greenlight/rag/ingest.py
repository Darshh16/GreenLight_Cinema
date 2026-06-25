"""
Greenlight Cinema — Hybrid RAG Ingestion v3
=============================================
Ingests BOTH sources into a single ChromaDB collection:

  Source 1: 50 Ollama-generated screenplay excerpts (data/generated_screenplays.json)
            - Short (150-250 word) cinematic scenes from top DuckDB movies
            - Stored as single chunks per screenplay

  Source 2: 100 real screenplay PDFs (data/scripts/*.pdf)
            - Full 100-150 page screenplays from SimplyScripts
            - Chunked by scene headers (INT./EXT.) with 450-word hard cap

The Writer agent gets the best of both worlds:
  - Ollama excerpts provide quick genre-specific tone references
  - Real screenplays provide authentic dialogue, pacing, and structure
"""

import re
import json
import hashlib
import logging
import shutil
from pathlib import Path

import pdfplumber
import chromadb
from chromadb.config import Settings

from greenlight.config import CHROMA_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL, SCRIPTS_DIR
from greenlight.rag.scripts import get_script_metadata, get_available_scripts

log = logging.getLogger("greenlight.rag.ingest")

# ── Chunking config ─────────────────────────────────────────────────────────
CHUNK_SIZE      = 400
CHUNK_OVERLAP   = 50
MIN_CHUNK_WORDS = 30
MAX_CHUNK_WORDS = 450
MIN_ALPHA_RATIO = 0.55
BATCH_SIZE      = 64

GENERATED_SCRIPTS_PATH = Path("data/generated_screenplays.json")

# Screenplay scene header pattern
SCENE_PATTERN = re.compile(r"(?m)^(INT\.|EXT\.|INT/EXT\.|I/E\.)\s+.+")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: Ollama-generated screenplay excerpts
# ══════════════════════════════════════════════════════════════════════════════

def _load_generated_scripts() -> list[tuple[str, dict, str]]:
    """
    Load the 50 Ollama-generated screenplay excerpts from the JSON cache.
    Returns list of (document_text, metadata, doc_id) tuples.
    """
    if not GENERATED_SCRIPTS_PATH.exists():
        log.warning(f"No generated screenplays found at {GENERATED_SCRIPTS_PATH}")
        return []

    with open(GENERATED_SCRIPTS_PATH, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    chunks = []
    for script in scripts:
        sid = script["id"]
        chunks.append((
            script["script"],
            {
                "source": f"generated_{sid}",
                "title": script["title"],
                "genre": script["genre"],
                "year": 0,
                "act": "full",
                "chunk_index": 0,
                "total_chunks": 1,
                "word_count": len(script["script"].split()),
                "origin": "ollama_generated",
            },
            f"gen_{sid}_full"
        ))

    log.info(f"  Source 1: Loaded {len(chunks)} Ollama-generated screenplay excerpts")
    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: Real screenplay PDFs
# ══════════════════════════════════════════════════════════════════════════════

def _is_garbled(text: str) -> bool:
    if not text or len(text.strip()) < 50:
        return True
    alpha_chars = sum(c.isalpha() for c in text)
    return (alpha_chars / max(len(text), 1)) < MIN_ALPHA_RATIO


def _extract_text(file_path: Path) -> str:
    """Extract text from either a .txt or .pdf file."""
    if file_path.suffix.lower() == ".txt":
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if not _is_garbled(text):
                return text
        except Exception as e:
            log.warning(f"  Failed to read text file {file_path.name}: {e}")
        return ""

    # Otherwise treat as PDF
    pdf_path = file_path
    
    # Tier 1: pdfplumber
    try:
        text_pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text_pages.append(page.extract_text() or "")
        full_text = "\n".join(text_pages)
        if not _is_garbled(full_text):
            return full_text
    except Exception as e:
        log.debug(f"  pdfplumber failed for {pdf_path.name}: {e}")

    # Tier 2: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(pages)
        if not _is_garbled(full_text):
            return full_text
    except Exception as e:
        log.debug(f"  pypdf failed for {pdf_path.name}: {e}")

    # Tier 3: OCR (optional deps)
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(str(pdf_path), dpi=200)
        ocr_text = "\n".join(pytesseract.image_to_string(img) for img in images)
        if not _is_garbled(ocr_text):
            return ocr_text
    except ImportError:
        pass
    except Exception:
        pass

    log.warning(f"  ✗ All extraction failed for {pdf_path.name}")
    return ""


def _assign_act(chunk_index: int, total_chunks: int) -> str:
    pct = chunk_index / max(total_chunks, 1)
    if pct < 0.25:
        return "act_1"
    elif pct < 0.75:
        return "act_2"
    else:
        return "act_3"


def _hard_cap_chunk(text: str) -> list[str]:
    words = text.split()
    if len(words) <= MAX_CHUNK_WORDS:
        return [text] if len(words) >= MIN_CHUNK_WORDS else []
    sub_chunks = []
    start = 0
    while start < len(words):
        end = min(start + MAX_CHUNK_WORDS, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.split()) >= MIN_CHUNK_WORDS:
            sub_chunks.append(chunk)
        if end == len(words):
            break
        start += MAX_CHUNK_WORDS - CHUNK_OVERLAP
    return sub_chunks


def _fixed_size_chunks(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.split()) >= MIN_CHUNK_WORDS:
            chunks.append(chunk)
        if end == len(words):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _scene_chunks(text: str) -> list[str]:
    boundaries = [m.start() for m in SCENE_PATTERN.finditer(text)]
    if len(boundaries) < 3:
        return []
    raw_scenes = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        scene = text[start:end].strip()
        if scene:
            raw_scenes.append(scene)

    merged = []
    buffer = ""
    for scene in raw_scenes:
        if len(scene.split()) < MIN_CHUNK_WORDS:
            buffer = (buffer + " " + scene).strip()
        else:
            if buffer:
                scene = (buffer + " " + scene).strip()
                buffer = ""
            for sub in _hard_cap_chunk(scene):
                merged.append(sub)

    if buffer.strip():
        if merged:
            combined = merged[-1] + " " + buffer.strip()
            if len(combined.split()) <= MAX_CHUNK_WORDS:
                merged[-1] = combined
            else:
                for sub in _hard_cap_chunk(buffer.strip()):
                    merged.append(sub)
        else:
            for sub in _hard_cap_chunk(buffer.strip()):
                merged.append(sub)
    return merged


def _chunk_script_text(text: str, script_name: str = "") -> list[str]:
    """Scene-based chunking with fixed-size fallback."""
    chunks = _scene_chunks(text)
    if not chunks:
        chunks = _fixed_size_chunks(text)
    safe = []
    for chunk in chunks:
        for sub in _hard_cap_chunk(chunk):
            safe.append(sub)
    return safe


def _make_chunk_id(source: str, chunk_index: int) -> str:
    raw = f"{source}_chunk_{chunk_index:05d}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _load_pdf_scripts() -> list[tuple[str, dict, str]]:
    """
    Extract and chunk all downloaded screenplay PDFs.
    Returns list of (document_text, metadata, doc_id) tuples.
    """
    pdf_files = get_available_scripts()
    if not pdf_files:
        log.info(f"  Source 2: No screenplay PDFs found in {SCRIPTS_DIR}")
        return []

    all_chunks = []
    failed = []

    for pdf_path in pdf_files:
        source = pdf_path.stem
        meta = get_script_metadata(pdf_path.name)

        text = _extract_text(pdf_path)
        if not text:
            failed.append(pdf_path.name)
            continue

        chunks = _chunk_script_text(text, script_name=source)
        if not chunks:
            failed.append(pdf_path.name)
            continue

        total_chunks = len(chunks)
        word_counts = [len(c.split()) for c in chunks]
        log.info(
            f"  {source}: {total_chunks} chunks | "
            f"words min={min(word_counts)} avg={int(sum(word_counts)/total_chunks)} "
            f"max={max(word_counts)}"
        )

        for i, chunk in enumerate(chunks):
            all_chunks.append((
                chunk,
                {
                    "source": source,
                    "title": meta["title"],
                    "genre": meta["genre"],
                    "year": meta["year"],
                    "act": _assign_act(i, total_chunks),
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "word_count": len(chunk.split()),
                    "origin": "simplyscripts_pdf",
                },
                _make_chunk_id(source, i),
            ))

    log.info(f"  Source 2: {len(all_chunks)} chunks from {len(pdf_files) - len(failed)} PDFs"
             f" ({len(failed)} failed)")
    return all_chunks


# ══════════════════════════════════════════════════════════════════════════════
# HYBRID INGESTION — merges both sources into ChromaDB
# ══════════════════════════════════════════════════════════════════════════════

def _get_embedding_fn():
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def ingest_to_chromadb(n_scripts: int = 100) -> int:
    """
    Hybrid ingestion: merges Ollama-generated excerpts + real PDF screenplays
    into a single ChromaDB collection.

    Returns:
        Total number of documents in ChromaDB after ingestion
    """
    log.info("== ChromaDB Hybrid RAG Ingestion v3 START ==")

    # ── Collect chunks from BOTH sources ──────────────────────────────────────
    all_docs = []
    all_metadatas = []
    all_ids = []
    seen_ids = set()

    # Source 1: Ollama-generated excerpts
    for doc_text, metadata, doc_id in _load_generated_scripts():
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            all_docs.append(doc_text)
            all_metadatas.append(metadata)
            all_ids.append(doc_id)

    # Source 2: Real screenplay PDFs
    for doc_text, metadata, doc_id in _load_pdf_scripts():
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            all_docs.append(doc_text)
            all_metadatas.append(metadata)
            all_ids.append(doc_id)

    if not all_docs:
        log.error("No documents from either source! Run data pipeline + download first.")
        return 0

    log.info(f"  Total chunks to ingest: {len(all_docs)}")

    # ── Initialize ChromaDB (fresh collection) ────────────────────────────────
    log.info("Initializing ChromaDB ...")
    chroma_path = str(CHROMA_DIR)
    try:
        shutil.rmtree(chroma_path, ignore_errors=True)
    except Exception:
        pass

    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False),
    )
    embedding_fn = _get_embedding_fn()

    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # ── Batch insert ──────────────────────────────────────────────────────────
    log.info(f"Inserting {len(all_docs)} documents into ChromaDB ...")
    for i in range(0, len(all_docs), BATCH_SIZE):
        batch_end = min(i + BATCH_SIZE, len(all_docs))
        collection.add(
            documents=all_docs[i:batch_end],
            metadatas=all_metadatas[i:batch_end],
            ids=all_ids[i:batch_end],
        )
        if (i // BATCH_SIZE) % 5 == 0:
            log.info(f"  Batch {i // BATCH_SIZE + 1}: {batch_end}/{len(all_docs)} docs")

    final_count = collection.count()
    log.info(f"ChromaDB collection '{CHROMA_COLLECTION}': {final_count} documents")
    log.info("== ChromaDB Hybrid RAG Ingestion v3 COMPLETE ==")

    return final_count
