"""
Knowledge base retriever — PDF books and gym_calculations.txt from Knowledge_db.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from config import CACHE_DIR
from pypdf import PdfReader

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
GYM_CALCULATIONS_FILE = "gym_calculations.txt"
CHUNK_MAX_CHARS = 1200


@dataclass
class DocumentChunk:
    source: str
    text: str
    tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.tokens:
            self.tokens = _tokenize(self.text)


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _file_hash(path: Path) -> str:
    """SHA-256 of file contents for deduplication."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class KnowledgeRetriever:
    """
    TF-IDF retriever over PDF training books and gym_calculations.txt
    in the Knowledge_db folder.
    """

    def __init__(self, knowledge_dir: Path, top_k: int = 8) -> None:
        self.knowledge_dir = knowledge_dir
        self.top_k = top_k
        self._chunks: list[DocumentChunk] = []
        self._idf: dict[str, float] = {}
        self._chunk_vectors: list[dict[str, float]] = []
        self._cache_path = CACHE_DIR / "knowledge_chunks.json"
        self._load_corpus()
        self._build_idf()
        self._chunk_vectors = [self._tfidf_vector(chunk.tokens) for chunk in self._chunks]

    def _load_corpus(self) -> None:
        if not self.knowledge_dir.is_dir():
            raise FileNotFoundError(
                f"Knowledge base folder not found: {self.knowledge_dir}"
            )

        cached = self._load_cache_if_valid()
        if cached is not None:
            self._chunks = cached
            return

        self._chunks = []
        self._ingest_gym_calculations()
        self._ingest_pdfs()
        self._save_cache()

        if not self._chunks:
            raise RuntimeError(
                f"No readable content found in {self.knowledge_dir}. "
                "Add PDF books and/or gym_calculations.txt."
            )

    def _source_fingerprint(self) -> dict[str, float]:
        fingerprint: dict[str, float] = {}
        gym_path = self.knowledge_dir / GYM_CALCULATIONS_FILE
        if gym_path.exists():
            fingerprint[str(gym_path)] = gym_path.stat().st_mtime

        for pdf_path in sorted(self.knowledge_dir.glob("*.pdf")):
            fingerprint[str(pdf_path)] = pdf_path.stat().st_mtime
        return fingerprint

    def _load_cache_if_valid(self) -> list[DocumentChunk] | None:
        if not self._cache_path.exists():
            return None

        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if payload.get("fingerprint") != self._source_fingerprint():
            return None

        return [
            DocumentChunk(source=item["source"], text=item["text"])
            for item in payload.get("chunks", [])
        ]

    def _save_cache(self) -> None:
        if not self._chunks:
            return

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fingerprint": self._source_fingerprint(),
            "chunks": [
                {"source": chunk.source, "text": chunk.text}
                for chunk in self._chunks
            ],
        }
        # Atomic write: write to temp file then rename to avoid corruption
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        fd, tmp_path = tempfile.mkstemp(
            dir=self._cache_path.parent, suffix=".tmp"
        )
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        os.replace(tmp_path, self._cache_path)

    def _ingest_gym_calculations(self) -> None:
        gym_path = self.knowledge_dir / GYM_CALCULATIONS_FILE
        if not gym_path.exists():
            return

        gym_text = gym_path.read_text(encoding="utf-8")
        for block in _split_gym_blocks(gym_text):
            self._chunks.append(
                DocumentChunk(source=GYM_CALCULATIONS_FILE, text=block)
            )

    def _ingest_pdfs(self) -> None:
        seen_hashes: set[str] = set()
        for pdf_path in sorted(self.knowledge_dir.glob("*.pdf")):
            file_hash = _file_hash(pdf_path)
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)

            source_name = pdf_path.name
            for chunk_text in _extract_pdf_chunks(pdf_path):
                self._chunks.append(
                    DocumentChunk(source=source_name, text=chunk_text)
                )

    def _build_idf(self) -> None:
        doc_count = len(self._chunks)
        if doc_count == 0:
            return

        df: Counter[str] = Counter()
        for chunk in self._chunks:
            for token in set(chunk.tokens):
                df[token] += 1

        self._idf = {
            token: math.log((1 + doc_count) / (1 + freq)) + 1.0
            for token, freq in df.items()
        }

    def _tfidf_vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = sum(counts.values()) or 1
        return {
            token: (count / total) * self._idf.get(token, 1.0)
            for token, count in counts.items()
        }

    @staticmethod
    def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        common = set(vec_a) & set(vec_b)
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, query: str) -> tuple[str, float]:
        query_tokens = _tokenize(query)
        query_vec = self._tfidf_vector(query_tokens)

        scored: list[tuple[float, DocumentChunk]] = []
        for chunk, chunk_vec in zip(self._chunks, self._chunk_vectors):
            score = self._cosine_similarity(query_vec, chunk_vec)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: self.top_k]
        max_score = top[0][0] if top else 0.0

        if not top:
            return (
                "No directly matching reference entries were found in the knowledge base.",
                0.0,
            )

        sections = [chunk.text for _, chunk in top]
        return "\n\n".join(sections), max_score


def _split_gym_blocks(text: str) -> Iterable[str]:
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("----") and current:
            yield "\n".join(current).strip()
            current = []
        elif line.strip():
            current.append(line.rstrip())
    if current:
        yield "\n".join(current).strip()


def _extract_pdf_chunks(pdf_path: Path) -> list[str]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return []

    pages: list[str] = []
    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append(page_text)

    if not pages:
        return []

    full_text = "\n\n".join(pages)
    return _split_text_chunks(full_text)


def _split_text_chunks(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if current and current_len + paragraph_len + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len += paragraph_len + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks
